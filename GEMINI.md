# GEMINI.md

This file provides guidance to Gemini CLI when working with code in this repository.

## Project Overview

ABA on Demand Automator — a Python desktop app that automates English course completion on the ABA on Demand platform (andrewbiggs.com). It logs in, marks lessons complete, and intelligently answers quizzes using cached answers, with a Tkinter GUI for monitoring.

## Running the Application

```bash
# First-time setup (installs Playwright + downloads Chromium)
./setup.sh          # macOS/Linux
setup.bat           # Windows (double-click or run in cmd)

# Run the app
python3 main.py     # macOS/Linux
run.bat             # Windows (uses pythonw for no console window)
```

**Single external dependency**: `playwright` (installed by setup scripts). No `requirements.txt` — stdlib only otherwise.

## Architecture

### Thread Model
- **Main thread**: Tkinter event loop (GUI)
- **Worker thread**: `AutomationEngine` runs `asyncio.run()` in a background thread
- Communication from engine → GUI via `on_state_change(AppState)` callback (never call Tkinter from the worker thread)

### Core Flow
```
main.py → ui/app.py (Tkinter)
             └── "Start" → AutomationEngine (threaded)
                               ├── Login (WordPress session)
                               ├── Enrollment check
                               └── Episode loop:
                                     ├── LessonRunner (mark lesson complete)
                                     └── QuizRunner (answer quiz + cache)
```

### Module Map

| Area | Module | Role |
|------|--------|------|
| `core/engine.py` | `AutomationEngine` | Orchestrator — login, enrollment, episode loop |
| `core/quiz_runner.py` | `QuizRunner` | Quiz answering with text-keyed answer cache |
| `core/lesson_runner.py` | `LessonRunner` | 5 fallback strategies for marking lessons complete |
| `core/browser.py` | `BrowserSession` | Playwright lifecycle, resource blocking, retry navigation |
| `core/progress_store.py` | `ProgressStore` | Thread-safe atomic JSON persistence |
| `core/state.py` | `AppState`, `EpisodeStatus` | Immutable UI state dataclasses |
| `ui/` (9 files) | — | Tkinter panels: header, credentials, options, control bar, episode grid, log panel, timing |
| `courses/base_course.py` | `CourseConfig`, `EpisodeConfig` | Course config schema |
| `courses/__init__.py` | `COURSE_REGISTRY` | Dict of all registered courses |
| `utils/` | — | Profile store, settings store, screenshots, Windows toast notifications |

### Data Storage (`data/`, git-ignored)

```json
// data/progress.json — nested by email → course_id
{
  "user@example.com": {
    "UEN20367": {
      "episodes": { "0": {"score": 100, "complete": true, "lesson_ok": true, "attempts": 3} },
      "answer_cache": {
        "44211": { "What does X mean?": "option text A" }
      }
    }
  }
}
```

Answer cache key = **question text** (not position), value = string (radio) or list (checkbox).

### Quiz Intelligence

QuizRunner learns answers through four sources (in priority order):
1. Inline feedback after "Check" click
2. Post-quiz results page (positional matching)
3. Review panel fallback
4. **Elimination**: If N-1 options all tried and failed → last one must be correct (auto-cached)

### Lesson Completion Strategies (tried in sequence)
1. Click `form.sfwd-mark-complete` directly
2. AJAX via `sfwd_data.sfwd_nonce`
3. AJAX via form `nonce` input
4. Seek video (Vimeo/YouTube/HTML5) then wait for form to appear
5. Force AJAX fallback

### Speed Modes
- `fast` = 0.25× delays, `normal` = 0.6×, `careful` = 1.5×
- All `asyncio.sleep()` calls in core/ must multiply by the speed factor

## Adding a New Course

1. Create `courses/COURSE_ID/config.py`:
```python
from courses.base_course import CourseConfig, EpisodeConfig

COURSE = CourseConfig(
    course_id="UEN99999",
    display_name="Course Name — N episodes",
    site_url="https://andrewbiggs.com",
    course_url="https://andrewbiggs.com/courses/...",
    course_post_id=12345,
    episodes=[
        EpisodeConfig("Ep 1", lesson_post_id=100, quiz_url="https://.../quiz/", quiz_post_id=101),
        # ...
    ],
)
```

2. Register in `courses/__init__.py`:
```python
from courses.uen99999.config import COURSE as _NEW
COURSE_REGISTRY[_NEW.course_id] = _NEW
```

`CourseConfig` also accepts CSS selector overrides (`quiz_lock_sel`, `start_btn_sel`, `answer_item_sel`, `restart_sels`) if the course HTML differs from the default.

## Key Implementation Notes

- `ProgressStore` uses `threading.Lock()` + atomic write (temp file → rename) to prevent JSON corruption on crash
- Playwright resource blocking (images, fonts, CSS aborted) is applied in `BrowserSession` to speed up page loads
- Session expiry is detected by checking if the login form reappears mid-session → triggers re-authentication
- The episode grid uses color coding: gray=pending, blue=running, green=done (100%), red=failed (<100%)
