import logging

import pytest
from pytest_mock import MockerFixture
from repo.wikipedia import WikipediaRestRepo


@pytest.fixture
def mock_2015_10_10() -> str:
    with open("test/fixture/day_counts_2015_10_10.json") as f:
        return f.read()


def test_wikipedia_2015_10_10(mocker: MockerFixture, mock_2015_10_10: str) -> None:
    logger = logging.Logger("test")
    r = WikipediaRestRepo(logger=logger, max_concurrency=1)
    mocker.patch.object(r, "_get_json", return_value=mock_2015_10_10)
    article_counts = r.top_articles_for_day(2015, 10, 10)
    assert article_counts
    main_page = article_counts[0]
    assert main_page.article_name == "Main_Page"
    assert main_page.article_count == 18793503
    napoleon = article_counts[-1]
    assert napoleon.article_name == "Napoleon"
    assert napoleon.article_count == 8871
