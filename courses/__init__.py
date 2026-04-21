from courses.uen20367.config import COURSE as _UEN20367
# ── เพิ่ม course ใหม่ที่นี่ ──────────────────────────────────────────────────
# from courses.uen99999.config import COURSE as _UEN99999

from courses.base_course import CourseConfig
from typing import Dict

COURSE_REGISTRY: Dict[str, CourseConfig] = {
    _UEN20367.course_id: _UEN20367,
    # _UEN99999.course_id: _UEN99999,
}
