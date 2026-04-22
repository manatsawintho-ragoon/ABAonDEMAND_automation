from courses.uen20367.config import COURSE as _UEN20367
from courses.mslearn.catalog import ALL_MSLEARN_COURSES

from courses.base_course import CourseConfig
from typing import Dict, Union

COURSE_REGISTRY: Dict[str, Union[CourseConfig, object]] = {
    _UEN20367.course_id: _UEN20367,
}

for _c in ALL_MSLEARN_COURSES:
    COURSE_REGISTRY[_c.course_id] = _c
