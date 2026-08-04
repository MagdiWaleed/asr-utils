from asr_utils.normalization import normalize_text, normalize_numbers


def test_normalize_numbers_arabic_words():
    assert normalize_numbers("ثلاثة عشر") == "13"


def test_normalize_numbers_english_words():
    assert normalize_numbers("twenty three") == "23"


def test_normalize_numbers_thousands_separator():
    assert normalize_numbers("100,000") == "100000"


def test_normalize_text_empty_string():
    assert normalize_text("") == ""


def test_normalize_text_enable_punc():
    assert normalize_text("Hello, World! twenty three books", enable_punc=["!", ","]) == "hello, world! 23 books"


def test_normalize_text_ellipsis_and_urdu_strip():
    assert normalize_text("مرحبا... كيف حالك؟") == "مرحبا كيف حالك"


def test_normalize_text_eot_token_custom():
    assert normalize_text("hello <eot> world", eot_token="<eot>") == "hello <eot> world"
    assert normalize_text("<eot> hello world", eot_token="<eot>") == "hello world"


def test_normalize_text_eot_token_default():
    # "<eot>" is protected even when eot_token isn't passed at all.
    assert normalize_text("hello <eot> world") == "hello <eot> world"
    assert normalize_text("<eot> hello world") == "hello world"


def test_normalize_text_strips_generic_tags():
    assert normalize_text("hello <afdaslk> world") == "hello world"
    assert normalize_text("<noise> hello <music> world <eot>") == "hello world <eot>"
    assert normalize_text("hello <> world") == "hello world"


def test_normalize_text_custom_eot_strips_other_tags_including_default():
    # once a custom eot_token is given, the literal "<eot>" is no longer
    # special, just another tag that gets stripped
    assert normalize_text("hello <turn> world <mytoken> bye", eot_token="<mytoken>") == "hello world <mytoken> bye"
    assert normalize_text("hello <eot> world", eot_token="<mytoken>") == "hello world"


def test_normalize_text_include_exclude_folding():
    assert normalize_text("آمن") == "امن"  # default: fold
    assert normalize_text("آمن", include_folding=["آ"]) == "امن"
    assert normalize_text("آمن", include_folding=["أ"]) == "آمن"  # unrelated char, no fold
    assert normalize_text("آمن", exclude_folding=["آ"]) == "آمن"
    assert normalize_text("آمن", include_folding=["آ"], exclude_folding=["آ"]) == "آمن"  # exclude wins


def test_normalize_text_enable_special_tokens():
    # kept, other tags still stripped, default eot still protected
    assert normalize_text(
        "hello <noise> world <eot> <music> bye", enable_special_tokens=["<noise>"]
    ) == "hello <noise> world <eot> bye"
    # multiple special tokens kept
    assert normalize_text(
        "<noise> hello <music> world <junk>", enable_special_tokens=["<noise>", "<music>"]
    ) == "<noise> hello <music> world"
    # combined with a custom eot_token
    assert normalize_text(
        "<sos> hi <mytoken> bye <junk>", eot_token="<mytoken>", enable_special_tokens=["<sos>"]
    ) == "<sos> hi <mytoken> bye"
    # not passed at all -> unaffected, still a generic stripped tag
    assert normalize_text("hello <noise> world") == "hello world"
    # unlike eot_token, a leading special token is NOT stripped
    assert normalize_text("<noise> hello world", enable_special_tokens=["<noise>"]) == "<noise> hello world"


def test_normalize_text_full():
    """Every option exercised in one call: enable_punc, custom eot_token
    (distinct from the "<eot>" default, proving the default stops being
    special once a custom one is given), enable_special_tokens,
    exclude_folding, number words, thousands separator, ellipsis
    collapsing, generic tag stripping, Urdu strip."""
    text = (
        "Hello, World!... <noise> Ahmed said twenty three years <mytoken> "
        "<junk> <sos> and <eot> 100,000 riyals آمن ٱحد كيف حالك؟"
    )
    result = normalize_text(
        text,
        enable_punc=[",", "!"],
        eot_token="<mytoken>",
        enable_special_tokens=["<sos>"],
        exclude_folding=["آ"],
    )
    assert result == (
        "hello, world! ahmed said 23 years <mytoken> <sos> and 100000 riyals آمن حد كيف حالك"
    )


if __name__ == "__main__":
    test_normalize_numbers_arabic_words()
    test_normalize_numbers_english_words()
    test_normalize_numbers_thousands_separator()
    test_normalize_text_empty_string()
    test_normalize_text_enable_punc()
    test_normalize_text_ellipsis_and_urdu_strip()
    test_normalize_text_eot_token_custom()
    test_normalize_text_eot_token_default()
    test_normalize_text_strips_generic_tags()
    test_normalize_text_custom_eot_strips_other_tags_including_default()
    test_normalize_text_include_exclude_folding()
    test_normalize_text_enable_special_tokens()
    test_normalize_text_full()
    print("ok")
