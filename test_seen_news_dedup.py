from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, SeenNews, make_news_key, mark_news_items_seen


def build_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )
    return SessionLocal()


def test_link_key_normalizes_tracking_params():
    first = make_news_key(
        {
            "title": "BTC ETF inflows rise",
            "link": "https://example.com/article/?utm_source=rss&id=1",
            "source": "Example",
        }
    )
    second = make_news_key(
        {
            "title": "BTC ETF inflows rise",
            "link": "https://EXAMPLE.com/article?id=1",
            "source": "Example",
        }
    )

    assert first == second
    assert first.startswith("link:")


def test_missing_link_fallback_uses_source_and_title():
    first = make_news_key({"title": "Same headline", "source": "Source A"})
    second = make_news_key({"title": "Same headline", "source": "Source B"})

    assert first != second
    assert first.startswith("source_title:")


def test_seen_news_insert_skips_duplicate_keys():
    session = build_session()
    try:
        mark_news_items_seen(
            session,
            [
                {
                    "title": "BTC ETF inflows rise",
                    "link": "https://example.com/article?id=1&utm_campaign=x",
                    "source": "Example",
                },
                {
                    "title": "Updated title should still dedupe by link",
                    "link": "https://example.com/article?id=1",
                    "source": "Example",
                },
            ],
        )

        assert session.query(SeenNews).count() == 1
    finally:
        session.close()


if __name__ == "__main__":
    test_link_key_normalizes_tracking_params()
    test_missing_link_fallback_uses_source_and_title()
    test_seen_news_insert_skips_duplicate_keys()
    print("seen_news dedup tests passed")
