import datetime
import logging
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from flask_restful import Resource
from werkzeug.exceptions import HTTPException

from model.article import ArticleCount
from repo.wikipedia import WikipediaRepo


class DataNotFoundException(HTTPException):
    """
    Exception raised when there is a request for data that does not exist.
    """
    pass


class TopViewsResponse(NamedTuple):
    article_counts: List[ArticleCount]

    def asdict(self) -> Dict[str, Any]:
        return {"article_counts": [c._asdict() for c in self.article_counts]}


class TopArticleForDayResponse(NamedTuple):
    year: int
    month: int
    day: int
    article_name: str
    article_count: int


class TopViewsForMonth(Resource):  # type: ignore

    def __init__(self, **kwargs: Any):
        logger: Optional[logging.Logger] = kwargs.get("logger") or None
        if not logger:
            raise ValueError("logger not provided")
        self._logger = logger
        wikipedia_repo: Optional[WikipediaRepo] = kwargs.get(
            "wikipedia_repo") or None
        if not wikipedia_repo:
            raise ValueError("wikipedia repository not provided")
        self._wikipedia_repo = wikipedia_repo

    def get(self, year: int, month: int) -> Dict[str, Any]:
        article_counts = self._wikipedia_repo.top_articles_for_month(
            year, month)
        return TopViewsResponse(article_counts=article_counts).asdict()


class TopViewsForWeek(Resource):  # type: ignore

    def __init__(self, **kwargs: Any):
        logger: Optional[logging.Logger] = kwargs.get("logger") or None
        if not logger:
            raise ValueError("logger not provided")
        self._logger = logger
        wikipedia_repo: Optional[WikipediaRepo] = kwargs.get(
            "wikipedia_repo") or None
        if not wikipedia_repo:
            raise ValueError("wikipedia repository not provided")
        self._wikipedia_repo = wikipedia_repo

    def get(self, year: int, week: int) -> Dict[str, Any]:
        article_counts = self._wikipedia_repo.top_articles_for_week(
            year, week)
        return TopViewsResponse(article_counts=article_counts).asdict()


class TopDayForArticle(Resource):  # type: ignore

    def __init__(self, **kwargs: Any):
        logger: Optional[logging.Logger] = kwargs.get("logger") or None
        if not logger:
            raise ValueError("logger not provided")
        self._logger = logger
        wikipedia_repo: Optional[WikipediaRepo] = kwargs.get(
            "wikipedia_repo") or None
        if not wikipedia_repo:
            raise ValueError("wikipedia repository not provided")
        self._wikipedia_repo = wikipedia_repo

    def get(self, article_name: str, year: int, month: int) -> Dict[str, Any]:
        article_counts_by_day = self._wikipedia_repo.top_articles_for_month_by_day(
            year, month)
        counts_for_article: List[Tuple[datetime.date, ArticleCount]] = []
        for count_date, article_counts in article_counts_by_day.items():
            for article_count in article_counts:
                if article_count.article_name == article_name:
                    counts_for_article.append((count_date, article_count))
        if counts_for_article:
            counts_for_article = sorted(
                counts_for_article, key=lambda c: c[1].article_count, reverse=True)
            top_count = counts_for_article[0]
            return TopArticleForDayResponse(top_count[0].year, top_count[0].month, top_count[0].day, top_count[1].article_name, top_count[1].article_count)._asdict()

        raise DataNotFoundException()
