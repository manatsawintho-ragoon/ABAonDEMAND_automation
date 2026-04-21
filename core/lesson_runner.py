import asyncio
from typing import Callable
from playwright.async_api import Page, TimeoutError as PwTimeout

from core.browser import BrowserSession
from courses.base_course import CourseConfig, EpisodeConfig

_JS_PAGE_STATE = """
() => ({
    formVisible: (() => {
        const f = document.querySelector('form.sfwd-mark-complete');
        return f ? f.offsetParent !== null : false;
    })(),
    sfwdNonce:  typeof sfwd_data !== 'undefined'
                    ? (sfwd_data.data || {}).sfwd_nonce : null,
    ajaxurl:    typeof sfwd_data !== 'undefined'
                    ? sfwd_data.ajaxurl : null,
    postId:     typeof sfwd_data !== 'undefined'
                    ? (sfwd_data.data || {}).post_id : null,
    courseId:   typeof sfwd_data !== 'undefined'
                    ? (sfwd_data.data || {}).course_id : null,
    hasVimeo:   !!document.querySelector('iframe[src*="vimeo"]'),
    hasYoutube: !!document.querySelector('iframe[src*="youtube"]'),
    hasHtml5:   !!document.querySelector('video'),
    hasLdPlayer:typeof ld_video_players !== 'undefined',
    formNonce:  document.querySelector(
                    'form.sfwd-mark-complete input[name="nonce"]')?.value || null,
    sessionOk:  !document.querySelector('#loginform'),
})
"""

_JS_FORM_VISIBLE = """
() => {
    const f = document.querySelector('form.sfwd-mark-complete');
    return f ? f.offsetParent !== null : false;
}
"""

_JS_SEEK_VIDEO = """
async () => {
    try {
        // LearnDash Vimeo player via ld_video_players
        if (typeof ld_video_players !== 'undefined') {
            const k = Object.keys(ld_video_players)[0];
            if (k) {
                const vp = ld_video_players[k].player;
                const d = await vp.getDuration();
                await vp.setCurrentTime(Math.max(0, d - 1));
                await vp.play();
                return { ok: true, type: 'ld_vimeo', dur: d };
            }
        }
        // Direct Vimeo iframe
        if (typeof Vimeo !== 'undefined') {
            const fr = document.querySelector('iframe[src*="vimeo"]');
            if (fr) {
                const vp = new Vimeo.Player(fr);
                const d = await vp.getDuration();
                await vp.setCurrentTime(Math.max(0, d - 1));
                await vp.play();
                return { ok: true, type: 'vimeo', dur: d };
            }
        }
        // HTML5 <video>
        const vid = document.querySelector('video');
        if (vid && vid.duration) {
            vid.currentTime = Math.max(0, vid.duration - 1);
            await vid.play().catch(() => {});
            return { ok: true, type: 'html5', dur: vid.duration };
        }
        // YouTube — trigger end via postMessage (best-effort)
        const ytFr = document.querySelector('iframe[src*="youtube"]');
        if (ytFr) {
            ytFr.contentWindow.postMessage(
                '{"event":"command","func":"seekTo","args":[999999,true]}', '*');
            return { ok: true, type: 'youtube_pm' };
        }
        return { ok: false };
    } catch(e) { return { ok: false, err: e.message }; }
}
"""


class LessonRunner:
    """Marks a LearnDash lesson complete. Tries multiple strategies with retries.
    Also detects session expiry and re-authenticates.
    """

    MAX_RETRIES = 3
    VIDEO_WAIT_S = 20

    def __init__(self, session: BrowserSession, course: CourseConfig,
                 on_log: Callable[[str], None],
                 email: str = "", password: str = ""):
        self._s = session
        self._c = course
        self._log = on_log
        self._email = email
        self._password = password

    async def complete(self, page: Page, ep: EpisodeConfig) -> bool:
        lesson_url = f"{self._c.site_url}/?p={ep.lesson_post_id}"
        for attempt in range(self.MAX_RETRIES):
            try:
                ok = await self._attempt(page, ep, lesson_url)
                if ok:
                    return True
                if attempt < self.MAX_RETRIES - 1:
                    await self._s.delay(1.5)
            except Exception as e:
                self._log(f"  [lesson retry {attempt+1}] {e}")
                await self._s.delay(1.5)
        self._log("  [lesson] ไม่สำเร็จหลัง 3 ครั้ง")
        return False

    async def _attempt(self, page: Page, ep: EpisodeConfig, lesson_url: str) -> bool:
        await self._s.navigate(page, lesson_url)
        await self._s.delay(1.0)

        state = await page.evaluate(_JS_PAGE_STATE)

        # Session expired → re-login
        if not state.get("sessionOk", True):
            self._log("  [lesson] session หมด → re-login…")
            if self._email and self._password:
                await self._relogin(page)
                await self._s.navigate(page, lesson_url)
                await self._s.delay(1.0)
                state = await page.evaluate(_JS_PAGE_STATE)
            else:
                self._log("  [lesson] ไม่มีข้อมูล login สำหรับ re-login")
                return False

        ajax    = state.get("ajaxurl")  or self._c.ajax_url
        nonce   = state.get("sfwdNonce")
        post_id = state.get("postId")   or str(ep.lesson_post_id)
        cid     = state.get("courseId") or str(self._c.course_post_id)

        # S1: form visible → click
        if state.get("formVisible"):
            self._log("  [lesson] form visible → click")
            return await self._click_mark_complete(page)

        # S2: AJAX with sfwdNonce
        if nonce:
            ok = await self._ajax_complete(page, ajax, nonce, post_id, cid)
            if ok:
                self._log("  [lesson] AJAX (sfwd_nonce) OK")
                return True

        # S3: AJAX with form nonce
        form_nonce = state.get("formNonce")
        if form_nonce and form_nonce != nonce:
            ok = await self._ajax_complete(page, ajax, form_nonce, post_id, cid)
            if ok:
                self._log("  [lesson] AJAX (form nonce) OK")
                return True

        # S4: seek video → wait for form
        has_video = any([state.get("hasVimeo"), state.get("hasLdPlayer"),
                         state.get("hasHtml5"), state.get("hasYoutube")])
        if has_video:
            r = await page.evaluate(_JS_SEEK_VIDEO)
            if r.get("ok"):
                self._log(f"  [lesson] video seek OK ({r.get('type')}) "
                          f"dur={r.get('dur','?')}s → รอ form…")
                for i in range(self.VIDEO_WAIT_S):
                    await asyncio.sleep(1.0 * self._s.speed_factor)
                    if await page.evaluate(_JS_FORM_VISIBLE):
                        self._log(f"  [lesson] form ปรากฏหลัง {i+1}s")
                        return await self._click_mark_complete(page)
            # Try nonce from form after seek
            n3 = await page.evaluate(
                "() => document.querySelector("
                "'form.sfwd-mark-complete input[name=\"nonce\"]')?.value || null")
            if n3:
                ok = await self._ajax_complete(page, ajax, n3, post_id, cid)
                if ok:
                    self._log("  [lesson] AJAX หลัง video seek OK")
                    return True

        # S5: force AJAX (no nonce)
        ok = await self._force_ajax(page, ajax, post_id, cid)
        if ok:
            self._log("  [lesson] force AJAX OK")
            return True

        return False

    async def _relogin(self, page: Page) -> None:
        try:
            await self._s.navigate(page, self._c.login_url)
            await page.fill("#user_login", self._email)
            await page.fill("#user_pass", self._password)
            await page.click("#wp-submit")
            await page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            self._log(f"  [lesson] re-login error: {e}")

    async def _ajax_complete(self, page: Page, url: str,
                             nonce: str, post_id: str, course_id: str) -> bool:
        try:
            res = await page.evaluate("""
                async ([url, nonce, pid, cid]) => {
                    const post = async (d) => {
                        const fd = new FormData();
                        Object.entries(d).forEach(([k,v]) => fd.append(k,v));
                        const r = await fetch(url,{method:'POST',body:fd,credentials:'include'});
                        return r.text();
                    };
                    const r1 = await post({
                        action:'sfwd_video_progression',
                        post_id:pid, course_id:cid, nonce,
                        video_position:'100', video_duration:'300'
                    });
                    const r2 = await post({
                        action:'sfwd_mark_complete',
                        post_id:pid, course_id:cid, nonce, sfwd_nonce:nonce
                    });
                    return { r1, r2 };
                }
            """, [url, nonce, str(post_id), str(course_id)])
            r2 = (res.get("r2") or "").strip()
            # Detect session expired in response
            if "wp-login" in r2 or "login_required" in r2:
                return False
            return bool(r2) and r2 not in ("0", "false") \
                   and "error" not in r2.lower()
        except Exception:
            return False

    async def _force_ajax(self, page: Page, url: str,
                          post_id: str, course_id: str) -> bool:
        """Mark complete without nonce — works on sites that skip nonce check."""
        try:
            res = await page.evaluate("""
                async ([url, pid, cid]) => {
                    const fd = new FormData();
                    fd.append('action','sfwd_mark_complete');
                    fd.append('post_id', pid);
                    fd.append('course_id', cid);
                    const r = await fetch(url,{method:'POST',body:fd,credentials:'include'});
                    return r.text();
                }
            """, [url, str(post_id), str(course_id)])
            r = (res or "").strip()
            return bool(r) and r not in ("0", "false") and "error" not in r.lower()
        except Exception:
            return False

    async def _click_mark_complete(self, page: Page) -> bool:
        try:
            btn = page.locator(
                "form.sfwd-mark-complete input[type=submit],"
                "form.sfwd-mark-complete button[type=submit]")
            if await btn.count() > 0:
                await btn.first.click()
                await page.wait_for_load_state("networkidle", timeout=15000)
                await self._s.delay(0.8)
                return True
        except Exception:
            pass
        return False
