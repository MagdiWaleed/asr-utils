from asr_utils.normalization import normalize_text, normalize_numbers
from asr_utils.normalization.normalization import MAP_LETTERS


def test_normalize_numbers_arabic_words():
    assert normalize_numbers("ثلاثة عشر") == "13"


def test_normalize_numbers_english_words():
    assert normalize_numbers("twenty three") == "23"


def test_normalize_numbers_thousands_separator():
    assert normalize_numbers("100,000") == "100000"


def test_normalize_numbers_leading_eot_alone_is_kept():
    # bug found via real benchmark data: an eot-only hypothesis ("<eot>",
    # ". <eot>") used to collapse to "" instead of staying "<eot>", losing
    # the "nothing said, just end of turn" signal entirely.
    assert normalize_text("<eot>") == "<eot>"
    assert normalize_text(". <eot>") == "<eot>"
    assert normalize_text("<eot> <eot>") == "<eot>"
    assert normalize_text("<eot> hello world") == "hello world"  # real content still strips leading eot


def test_normalize_numbers_chained_multiplier_product():
    # bug A: chained multipliers must multiply, not sum
    assert normalize_numbers("مائة ألف") == "100000"
    assert normalize_numbers("خمسة مائة الف") == "500000"  # SINGLE + MULT + MULT chain
    assert normalize_numbers("خمسة عشر الف") == "15000"    # baseline must not regress


def test_normalize_numbers_fused_waw_connector():
    # bug B: "و" glued to the next number word with no space
    assert normalize_numbers("الفين وتسعه عشر") == "2019"
    assert normalize_numbers("ألف ومئة") == "1100"


def test_normalize_numbers_dual_forms():
    # bug C: dual-inflected "two thousand"/"two hundred" as one word
    assert normalize_numbers("ألفين وست مئة") == "2600"
    assert normalize_numbers("ميتين و سبع مية") == "900"
    assert normalize_numbers("مئتين الف") == "200000"  # dual directly chained into a multiplier


def test_normalize_numbers_million_billion():
    # bug D
    assert normalize_numbers("ستين مليون") == "60000000"


def test_normalize_numbers_colloquial_hundred_spelling():
    # bug E: "مية"/"ميه"/"مئه" alongside the existing "مائة"/"مئة"
    assert normalize_numbers("خمس مية") == "500"
    assert normalize_numbers("الف وست مئه وثلاثه وثمانين") == "1683"


def test_normalize_numbers_glued_hundred_compounds():
    # found via real corpus data, not in the original bug list: "ثلاثمائة"
    # etc. are one fused word (300-900), not "SINGLE space MULT"
    assert normalize_numbers("ستمائة ألف") == "600000"
    assert normalize_numbers("خمسمائة طالب") == "500 طالب"
    assert normalize_numbers("تسعمية وسبعين") == "970"


def test_normalize_numbers_dialect_fused_teens():
    # bug G
    assert normalize_numbers("خمس طعش") == "15"
    assert normalize_numbers("ثلاث طعشر") == "13"


def test_normalize_numbers_tanwin_carrier_alif():
    # diacritic-timing bug: a tanwin-carrier alif on a number word
    assert normalize_numbers("ثلاثاً و عشرين") == "23"


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


def test_normalize_text_letter_folding():
    assert normalize_text("آمن") == "امن"
    assert normalize_text("أحمد") == "احمد"
    assert normalize_text("إنسان") == "انسان"


def test_normalize_text_map_letters_override():
    # add an entry on top of the default
    added = {**MAP_LETTERS, "ة": "ه"}
    assert normalize_text("مدرسة", map_letters=added) == "مدرسه"
    # drop an entry: only آ folds, أ no longer does
    minimal = {"آ": "ا"}
    assert normalize_text("آمن أحمد", map_letters=minimal) == "امن أحمد"
    # default unaffected when not passed
    assert normalize_text("آمن أحمد") == "امن احمد"


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
    special once a custom one is given), enable_special_tokens, letter
    folding, number words, thousands separator, ellipsis collapsing,
    generic tag stripping, Urdu strip."""
    text = (
        "Hello, World!... <noise> Ahmed said twenty three years <mytoken> "
        "<junk> <sos> and <eot> 100,000 riyals آمن ٱحد كيف حالك؟"
    )
    result = normalize_text(
        text,
        enable_punc=[",", "!"],
        eot_token="<mytoken>",
        enable_special_tokens=["<sos>"],
    )
    assert result == (
        "hello, world! ahmed said 23 years <mytoken> <sos> and 100000 riyals امن احد كيف حالك"
    )


if __name__ == "__main__":
    test_normalize_numbers_arabic_words()
    test_normalize_numbers_english_words()
    test_normalize_numbers_thousands_separator()
    test_normalize_numbers_leading_eot_alone_is_kept()
    test_normalize_numbers_chained_multiplier_product()
    test_normalize_numbers_fused_waw_connector()
    test_normalize_numbers_dual_forms()
    test_normalize_numbers_million_billion()
    test_normalize_numbers_colloquial_hundred_spelling()
    test_normalize_numbers_glued_hundred_compounds()
    test_normalize_numbers_dialect_fused_teens()
    test_normalize_numbers_tanwin_carrier_alif()
    test_normalize_text_empty_string()
    test_normalize_text_enable_punc()
    test_normalize_text_ellipsis_and_urdu_strip()
    test_normalize_text_eot_token_custom()
    test_normalize_text_eot_token_default()
    test_normalize_text_strips_generic_tags()
    test_normalize_text_custom_eot_strips_other_tags_including_default()
    test_normalize_text_letter_folding()
    test_normalize_text_map_letters_override()
    test_normalize_text_enable_special_tokens()
    test_normalize_text_full()
    print("ok")
