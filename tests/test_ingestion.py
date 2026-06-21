from app.ingestion import day, instant, integer, number, text


def test_ingestion_converters():
    assert text("  value ") == "value"
    assert text("") is None
    assert str(number("12.34")) == "12.34"
    assert number("") is None
    assert integer("4") == 4
    assert day("2021-11-19").year == 2021
    assert instant("2021-11-19T12:00:00Z").tzinfo is not None

