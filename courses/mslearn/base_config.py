from dataclasses import dataclass, field
from typing import List


@dataclass
class MSLearnModuleConfig:
    module_id: str   # slug, e.g. "intro-to-git"
    title: str       # display name
    url: str         # https://learn.microsoft.com/en-us/training/modules/.../

    # --- duck-type compat with EpisodeConfig so EpisodeGrid works unchanged ---
    @property
    def name(self) -> str:
        return self.title

    @property
    def quiz_url(self) -> str:
        return self.url

    @property
    def quiz_post_id(self) -> int:
        return 0

    @property
    def lesson_post_id(self) -> int:
        return 0


@dataclass
class MSLearnCourseConfig:
    course_id: str
    display_name: str
    modules: List[MSLearnModuleConfig]
    locale: str = "en-us"
    provider: str = "mslearn"
    min_score: int = 100
    max_retry: int = 3

    # --- duck-type compat with CourseConfig ---
    @property
    def episodes(self) -> List[MSLearnModuleConfig]:
        return self.modules

    @property
    def menu_name(self) -> str:
        """Short name for the UI course dropdown (strips 'MS Learn — ' prefix)."""
        name = self.display_name.replace("MS Learn — ", "")
        return name[:46] + "…" if len(name) > 46 else name

    @property
    def base_url(self) -> str:
        return f"https://learn.microsoft.com/{self.locale}"

    @property
    def training_url(self) -> str:
        return f"{self.base_url}/training/"
