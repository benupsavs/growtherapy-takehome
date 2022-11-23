from abc import ABC, abstractmethod
from concurrent.futures import Future, ThreadPoolExecutor
import datetime
import json
import logging
from typing import Dict, Iterable, List, Optional, Tuple

from werkzeug.exceptions import HTTPException

import redis
import requests
from date.resolvers import days_in_month, days_in_week
from model.article import ArticleCount


class WikipediaFetchException(HTTPException):
    """
    Exception raised when there is an issue fetching article counts from Wikipedia.
    """
    pass


class WikipediaRepo(ABC):

    @abstractmethod
    def top_articles_for_month(self, year: int, month: int) -> List[ArticleCount]:
        pass

    @abstractmethod
    def top_articles_for_month_by_day(self, year: int, month: int) -> Dict[datetime.date, List[ArticleCount]]:
        pass

    @abstractmethod
    def top_articles_for_day(self, year: int, month: int, day: int) -> List[ArticleCount]:
        pass

    @abstractmethod
    def top_articles_for_week(self, year: int, week: int) -> List[ArticleCount]:
        pass

    @staticmethod
    def counts_to_json(article_counts: List[ArticleCount]) -> str:
        return json.dumps([a._asdict() for a in article_counts])

    @staticmethod
    def json_to_counts(encoded: str | bytes) -> List[ArticleCount]:
        decoded_list = json.loads(encoded)
        return [ArticleCount(**a) for a in decoded_list]


class WikipediaRestRepo(WikipediaRepo):
    _WIKIPEDIA_URL_TEMPLATE = "https://wikimedia.org/api/rest_v1/metrics/pageviews/top/en.wikipedia/all-access/{:d}/{:02d}/{:02d}"
    _HEADERS = {"user-agent": "grow-therapy-takehome-project/1.0",
                "accept": "application/json"}

    def __init__(self, max_concurrency: int, logger: logging.Logger):
        self._worker_pool = ThreadPoolExecutor(max_workers=max_concurrency)
        self._logger = logger
        self._logger.info("instantiated rest repo")

    def top_articles_for_day(self, year: int, month: int, day: int) -> List[ArticleCount]:
        """
        Fetch article counts by day from Wikipedia's REST API.
        :raises: WikipediaFetchException if an error occurs while fetching data.
        """
        url = self._url_for_date(year, month, day)
        response_json = self._worker_pool.submit(
            self._get_json, url).result()
        response_dict = json.loads(response_json)
        if response_dict.get("items"):
            return [ArticleCount(r.get("article"), r.get("views"), year=year, month=month, day=day) for r in response_dict.get("items")[0].get("articles")]
        return []

    def top_articles_for_month(self, year: int, month: int) -> List[ArticleCount]:
        raise AttributeError("not implemented; caching required")

    def top_articles_for_month_by_day(self, year: int, month: int) -> Dict[datetime.date, List[ArticleCount]]:
        raise AttributeError("not implemented; caching required")

    def top_articles_for_week(self, year: int, week: int) -> List[ArticleCount]:
        raise AttributeError("not implemented; caching required")

    def _url_for_date(self, year: int, month: int, day: int) -> str:
        return self._WIKIPEDIA_URL_TEMPLATE.format(year, month, day)

    def _get_json(self, uri: str) -> str:
        self._logger.debug("fetch %s", uri)
        response = requests.get(uri, headers=self._HEADERS)
        if not response.ok:
            raise WikipediaFetchException(
                "unable to fetch article counts: {}".format(response.reason))
        return str(response.content, "utf-8")


class WikipediaCachingRepo(WikipediaRepo):

    _COUNTS_BY_DAY_KEY = "counts.day.{:d}.{:02d}.{:02d}"
    _COUNTS_BY_MONTH_KEY = "counts.month.{:d}.{:02d}"
    _COUNTS_BY_WEEK_KEY = "counts.week.{:d}.{:02d}"
    _LOCK_NAME_DAY = "lock.day"
    _LOCK_NAME_MONTH = "lock.month"

    def __init__(self, delegate: WikipediaRepo, redis: "redis.Redis[bytes]", logger: logging.Logger):
        self._delegate = delegate
        self._redis = redis
        self._logger = logger
        self._logger.info("instantiated caching repo")

    def top_articles_for_month(self, year: int, month: int) -> List[ArticleCount]:
        """
        Get top articles for the given month in the given year.
        :raises ValueError: if all days in the given month are in the future.
        """
        today = datetime.date.today()

        if today.year < year or (today.year == year and today.month < month):
            raise ValueError(
                "the requested year and month must not be in the future")
        elif today.year == year and today.month == month:
            self._logger.debug("not caching the summary for the current month")
            summary_cache = False
        else:
            summary_cache = True

        def fetch_aggregate() -> Tuple[List[ArticleCount], bytes]:
            month_days = days_in_month(year, month)
            day_results = self._fetch_day_results(month_days)
            result = self._aggregate(
                day_results.values(), year=year, month=month)
            return result, bytes(self.counts_to_json(result), "utf-8")

        result = None
        if summary_cache:
            key = self._COUNTS_BY_MONTH_KEY.format(year, month)
            result_bytes = self._redis.get(key)
            if not result_bytes:
                # Cache miss
                with self._redis.lock(self._LOCK_NAME_MONTH):
                    # double-checked locking
                    self._logger.info(
                        "cache miss for month %04d-%02d", year, month)
                    result_bytes = self._redis.get(key)
                    if not result_bytes:
                        result, result_bytes = fetch_aggregate()
                        self._redis.set(key, result_bytes)
            else:
                self._logger.info("cache hit for month %04d-%02d", year, month)
        else:
            # Cache disabled for the current month
            result, _ = fetch_aggregate()
        assert result_bytes
        return result or self.json_to_counts(result_bytes)

    def top_articles_for_month_by_day(self, year: int, month: int) -> Dict[datetime.date, List[ArticleCount]]:
        """
        Get top articles for the given month in the given year.
        :raises ValueError: if all days in the given month are in the future.
        """
        today = datetime.date.today()

        if today.year < year or (today.year == year and today.month < month):
            raise ValueError(
                "the requested year and month must not be in the future")

        month_days = days_in_month(year, month)
        if year == today.year and month == today.month:
            month_days = filter(lambda d: d < today, month_days)
        return self._fetch_day_results(month_days)

    def top_articles_for_week(self, year: int, week: int) -> List[ArticleCount]:
        """
        Get top articles for the given week in the given year.
        :raises ValueError: if all days in the given week are in the future.
        """
        today = datetime.date.today()
        week_days = days_in_week(year, week)

        if all([d >= today for d in week_days]):
            raise ValueError(
                "the requested year and week must not be completely in the future (or today)")
        elif any([d >= today for d in week_days]):
            self._logger.debug("not caching the summary for the current week")
            summary_cache = False
        else:
            summary_cache = True

        week_days = filter(lambda d: d < today, week_days)

        def fetch_aggregate() -> Tuple[List[ArticleCount], bytes]:
            day_results = self._fetch_day_results(week_days)
            result = self._aggregate(
                day_results.values(), year=year, week=week)
            return result, bytes(self.counts_to_json(result), "utf-8")

        result = None
        if summary_cache:
            key = self._COUNTS_BY_WEEK_KEY.format(year, week)
            result_bytes = self._redis.get(key)
            if not result_bytes:
                # Cache miss
                with self._redis.lock(self._LOCK_NAME_MONTH):
                    # double-checked locking
                    self._logger.info(
                        "cache miss for week %04d-%02d", year, week)
                    result_bytes = self._redis.get(key)
                    if not result_bytes:
                        result, result_bytes = fetch_aggregate()
                        self._redis.set(key, result_bytes)
            else:
                self._logger.info("cache hit for week %04d-%02d", year, week)
        else:
            # Cache disabled for the current month
            result, result_bytes = fetch_aggregate()
        assert result_bytes
        return result or self.json_to_counts(result_bytes)

    def top_articles_for_day(self, year: int, month: int, day: int) -> List[ArticleCount]:
        key = self._COUNTS_BY_DAY_KEY.format(year, month, day)
        result_bytes = self._redis.get(key)
        result = None
        if not result_bytes:
            # Cache miss
            with self._redis.lock(self._LOCK_NAME_DAY):
                # double-checked locking
                result_bytes = self._redis.get(key)
                if not result_bytes:
                    self._logger.info(
                        "cache miss for day %04d-%02d-%02d", year, month, day)
                    result = self._delegate.top_articles_for_day(
                        year, month, day)
                    result_bytes = bytes(self.counts_to_json(result), "utf-8")
                    self._redis.set(key, result_bytes)
        else:
            self._logger.info(
                "cache hit for day %04d-%02d-%02d", year, month, day)
        return result or self.json_to_counts(result_bytes)

    def _fetch_day_results(self, days: Iterable[datetime.date]) -> Dict[datetime.date, List[ArticleCount]]:
        """
        Fetch article counts in parallel, and return them grouped by day.
        :param days: an iterable of days to fetch for
        :return: results grouped by day, in an unordered dict
        """
        result: Dict[datetime.date, List[ArticleCount]] = {}
        futures: List[Future[List[ArticleCount]]] = []
        for d in days:
            with ThreadPoolExecutor(max_workers=31) as executor:
                futures.append(executor.submit(
                    self.top_articles_for_day, d.year, d.month, d.day))
        for f in futures:
            article_counts = f.result()
            if article_counts:
                first = article_counts[0]
                assert first.month
                assert first.day
                d = datetime.date(first.year, first.month, first.day)
                result[d] = article_counts
        return result

    def _aggregate(self, nested_article_counts: Iterable[List[ArticleCount]], year: int, month: Optional[int] = None, week: Optional[int] = None) -> List[ArticleCount]:
        """
        Merge and sort nested article counts.
        :param nested_article_counts: an iterable of counts by day
        """
        counts_by_article: Dict[str, ArticleCount] = {}
        for day_counts in nested_article_counts:
            for article_count in day_counts:
                current_article_sum = counts_by_article.get(
                    article_count.article_name)
                if current_article_sum is None:
                    new_count = article_count.article_count
                else:
                    new_count = current_article_sum.article_count + article_count.article_count
                counts_by_article[article_count.article_name] = ArticleCount(
                    article_name=article_count.article_name, article_count=new_count, year=year, month=month, week=week)

        sorted_article_counts: List[ArticleCount] = sorted(
            counts_by_article.values(), key=lambda i: i.article_count, reverse=True)

        return sorted_article_counts
