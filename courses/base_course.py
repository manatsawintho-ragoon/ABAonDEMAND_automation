from dataclasses import dataclass, field
from typing import List


@dataclass
class EpisodeConfig:
    name: str
    lesson_post_id: int
    quiz_url: str
    quiz_post_id: int


@dataclass
class CourseConfig:
    course_id: str           # unique key, e.g. "UEN20367"
    display_name: str        # shown in dropdown
    site_url: str            # e.g. https://ondemand.andrewbiggs.com
    course_url: str          # full course page URL
    course_post_id: int      # LearnDash course ID for AJAX
    episodes: List[EpisodeConfig]
    min_score: int = 100
    max_retry: int = 10

    # CSS selector overrides (change if another site uses different structure)
    quiz_lock_sel: str   = ".wpProQuiz_lock"
    start_btn_sel: str   = "input[name=startQuiz]"
    answer_item_sel: str = ("ul.wpProQuiz_questionList > "
                            "li.wpProQuiz_questionListItem")
    restart_sels: List[str] = field(default_factory=lambda: [
        ".wpProQuiz_button_restartQuiz",
        ".wpProQuiz_button_reShowQuestion",
        "input[name=reShowQuestion]",
        "input[value*='Restart']",
        "a:has-text('Restart')",
    ])

    @property
    def menu_name(self) -> str:
        name = self.display_name
        return name[:46] + "…" if len(name) > 46 else name

    @property
    def login_url(self) -> str:
        return f"{self.site_url}/wp-login.php"

    @property
    def ajax_url(self) -> str:
        return f"{self.site_url}/wp-admin/admin-ajax.php"
