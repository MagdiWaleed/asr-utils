from asr_normalization import normalize_text, normalize_numbers


def test_normalize_numbers_arabic_words():
    assert normalize_numbers("ثلاثة عشر") == "13"


def test_normalize_numbers_english_words():
    assert normalize_numbers("twenty three") == "23"


def test_normalize_numbers_thousands_separator():
    assert normalize_numbers("100,000") == "100000"


def test_normalize_text_enable_punc():
    assert normalize_text("Hello, World! twenty three books", enable_punc=["!", ","]) == "hello, world! 23 books"


def test_normalize_text_ellipsis_and_urdu_strip():
    assert normalize_text("مرحبا... كيف حالك؟") == "مرحبا كيف حالك"


def test_normalize_text_eot_token():
    assert normalize_text("hello <eot> world", eot_token="<eot>") == "hello <eot> world"
    assert normalize_text("<eot> hello world", eot_token="<eot>") == "hello world"


if __name__ == "__main__":
    test_normalize_numbers_arabic_words()
    test_normalize_numbers_english_words()
    test_normalize_numbers_thousands_separator()
    test_normalize_text_enable_punc()
    test_normalize_text_ellipsis_and_urdu_strip()
    test_normalize_text_eot_token()
    print("ok")
