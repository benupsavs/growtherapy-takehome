from typing import NamedTuple, Optional


class ArticleCount(NamedTuple):
    """
    Represents a count of articles for a specific month, day, or week.
    """
    article_name: str
    article_count: int
    year: int
    month: Optional[int] = None
    week: Optional[int] = None
    day: Optional[int] = None
