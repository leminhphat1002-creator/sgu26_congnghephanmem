"""Kiểm thử chuẩn hóa khóa cache nội dung."""

from app.modules.content.service import ContentService


def test_cache_title_case_insensitive():
    expected = "dinh độc lập"

    assert ContentService.normalize_cache_title("Dinh Độc Lập") == expected
    assert ContentService.normalize_cache_title("dinh độc lập") == expected
    assert ContentService.normalize_cache_title("DINH ĐỘC LẬP") == expected


def test_cache_title_trims_spaces():
    assert ContentService.normalize_cache_title("  Dinh Độc Lập  ") == "dinh độc lập"


def test_cache_title_unicode_normalization():
    composed = "Độc Lập"
    decomposed = "Đo\u0323̂c Lập"

    assert ContentService.normalize_cache_title(composed) == ContentService.normalize_cache_title(
        decomposed
    )
