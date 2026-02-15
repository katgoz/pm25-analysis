from src.literature.pubmed_fetch import build_query, record_to_article_dict


def test_build_query():
    cfg = {"pubmed": {"keyword": "PM2.5 health"}}

    q = build_query(cfg, "2024")

    assert "PM2.5 health" in q
    assert '"2024"[PDAT]' in q


def test_record_to_article_dict_basic():
    record = {
        "PMID": "123",
        "TI": "Air pollution study",
        "JT": "Science",
        "AU": ["Kowalski A", "Nowak B"],
        "AB": "Some abstract"
    }

    article = record_to_article_dict(record, "2024")

    assert article["pmid"] == "123"
    assert article["title"] == "Air pollution study"
    assert article["journal"] == "Science"
    assert article["year"] == "2024"
    assert article["authors"] == "Kowalski A; Nowak B"
    assert article["abstract"] == "Some abstract"


def test_record_to_article_dict_missing_fields():
    article = record_to_article_dict({}, "2024")

    assert article["pmid"] == ""
    assert article["title"] == ""
    assert article["journal"] == ""
    assert article["year"] == "2024"
    assert article["authors"] == ""
    assert article["abstract"] == ""
