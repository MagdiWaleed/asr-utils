from asr_normalization import normalize_text, normalize_numbers


def test_normalize_numbers_arabic_words():
    assert normalize_numbers("ثلاثة عشر") == "13"


def test_normalize_numbers_english_words():
    assert normalize_numbers("twenty three") == "23"


def test_normalize_text_arabic():
    assert normalize_text("أحمد") == "احمد"
    assert normalize_text("مدرسة!") == "مدرسه"


def test_normalize_text_english():
    assert normalize_text("Hello, World! twenty three books") == "hello world 23 books"


def test_normalize_text_enable_punc():
    assert normalize_text("hello!", enable_punc=["!"]) == "hello!"


if __name__ == "__main__":
    test_normalize_numbers_arabic_words()
    test_normalize_numbers_english_words()
    test_normalize_text_arabic()
    test_normalize_text_english()
    test_normalize_text_enable_punc()
    print("ok")
