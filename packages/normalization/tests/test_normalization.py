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
    # the "nothing said, just end of turn" signal entirely. Only applies
    # when eot_token is actually given, see test_normalize_text_eot_token_*.
    assert normalize_text("<eot>", eot_token="<eot>") == "<eot>"
    assert normalize_text(". <eot>", eot_token="<eot>") == "<eot>"
    assert normalize_text("<eot> <eot>", eot_token="<eot>") == "<eot>"
    assert normalize_text("<eot> hello world", eot_token="<eot>") == "hello world"  # real content still strips leading eot


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


def test_normalize_numbers_plural_thousands():
    # plural "thousands" was missing while plural "millions" was present, so
    # this came out half-converted as "3 الاف 207"
    assert normalize_numbers("ثلاثة آلاف ومائتين وسبع") == "3207"
    assert normalize_numbers("عشرة الاف") == "10000"
    # without a number before them they mean "thousands of", not 1000
    assert normalize_numbers("آلاف الأشخاص") == "آلاف الأشخاص"
    assert normalize_numbers("ملايين الناس") == "ملايين الناس"
    assert normalize_numbers("خمسة ملايين") == "5000000"


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
    # same, with the mark typed before the alif (used to give "ثلاثا 20")
    assert normalize_numbers("ثلاثًا و عشرين") == "23"
    assert normalize_numbers("اربعاً") == "4"
    # hamza-spelled number word converts the same as the bare-alif spelling
    assert normalize_numbers("أربعاً") == "4"


def test_normalize_text_tanwin_alif_folds_to_plain_alif():
    # The carrier alif is an alif variant, not noise: it folds to ا like أ/إ/آ,
    # it must not be deleted. Used to truncate: "شكراً" -> "شكر".
    assert normalize_text("شكراً") == "شكرا"
    assert normalize_text("طبعاً") == "طبعا"
    assert normalize_text("جداً") == "جدا"
    assert normalize_text("أيضاً") == "ايضا"
    # both codepoint orders give the same result
    assert normalize_text("جداً") == normalize_text("جدًا") == "جدا"
    # standalone normalize_numbers must not truncate non-number words either
    assert normalize_numbers("شكراً جزيلاً") == "شكرا جزيلا"


def test_normalize_numbers_edge_connectors_survive():
    # a connector at the edge of a number span is ordinary text, not arithmetic
    assert normalize_numbers("عندي ثلاثة و احنا رايحين") == "عندي 3 و احنا رايحين"
    assert normalize_numbers("قال و ثلاثة كمان") == "قال و 3 كمان"
    assert normalize_numbers("جبت وخمسة اقلام") == "جبت و 5 اقلام"
    assert normalize_numbers("one and we left") == "1 and we left"
    # connectors still sum *inside* a number
    assert normalize_numbers("خمسة وعشرين") == "25"
    assert normalize_numbers("ألف ومئة") == "1100"


def test_normalize_numbers_connector_only_span_is_not_zero():
    assert normalize_numbers("هو و و راح") == "هو و و راح"
    assert normalize_numbers("and and then") == "and and then"


def test_normalize_numbers_two_ones_joined_by_connector_are_a_list():
    assert normalize_numbers("ثلاثة و اربعة") == "3 و 4"
    assert normalize_numbers("one and two") == "1 and 2"
    # a one followed by a tens word is still a single number
    assert normalize_numbers("واحد و عشرين") == "21"
    # "واحد" itself starts with و but is not a fused connector
    assert normalize_numbers("قابلت واحد صاحبي") == "قابلت 1 صاحبي"
    assert normalize_numbers("وواحد") == "و 1"


def test_normalize_numbers_case_insensitive_english():
    assert normalize_numbers("One hundred") == "100"
    assert normalize_numbers("FIVE people") == "5 people"
    assert normalize_text("Twenty Three") == "23"


def test_normalize_numbers_hamza_spelled_words():
    assert normalize_numbers("أربعة") == normalize_numbers("اربعة") == "4"
    assert normalize_numbers("أربعين") == "40"
    assert normalize_numbers("إثنين") == "2"
    # "أحد" is left alone on purpose: usually "someone", not "one"
    assert normalize_text("لا أحد") == "لا احد"


def test_normalize_numbers_decomposed_unicode():
    import unicodedata
    assert normalize_numbers(unicodedata.normalize("NFD", "أربعة")) == "4"
    assert normalize_text(unicodedata.normalize("NFD", "شكراً")) == "شكرا"


def test_normalize_numbers_separate_numbers_stay_separate():
    assert normalize_numbers("في 2020 3 مرات") == "في 2020 3 مرات"
    assert normalize_numbers("2 0 2 4") == "2024"
    assert normalize_numbers("من 2019,2020") == "من 2019,2020"
    assert normalize_numbers("1,234,567") == "1234567"
    assert normalize_numbers("100,000, then") == "100000, then"


def test_normalize_numbers_vowelled_number_words():
    # a diacritic right after a number word used to split the number in two
    assert normalize_numbers("ألفٍ وسبعمائة وثلاثة وتسعين") == "1793"
    assert normalize_numbers("خمسةٍ وعشرين") == "25"
    assert normalize_numbers("ثلاثةُ آلافٍ") == normalize_numbers("ثلاثة آلاف") == "3000"
    assert normalize_text("جـداً") == "جدا"


def test_normalize_numbers_extended_arabic_indic_digits():
    assert normalize_numbers("٣ كتب ۳ كتب") == "3 كتب 3 كتب"


def test_normalize_text_persian_lookalike_letters_fold():
    assert normalize_text("کتاب یوم") == "كتاب يوم"
    assert normalize_text("اثنین") == "2"


def test_normalize_text_presentation_forms_decompose():
    assert normalize_text("ﻻ يوجد") == "لا يوجد"
    assert normalize_text("ﻣﺮﺣﺒﺎ") == "مرحبا"
    assert normalize_text("قال ﷲ") == "قال الله"


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
    # no eot_token given -> no eot protection at all, "<eot>" is just
    # another tag and gets stripped like any other.
    assert normalize_text("hello <eot> world") == "hello world"
    assert normalize_text("<eot> hello world") == "hello world"
    assert normalize_text("<eot>") == ""


def test_normalize_text_eot_token_custom_marker_variants():
    # only the exact provided token is kept, whatever it looks like
    assert normalize_text("hello <endofturn> world", eot_token="<endofturn>") == "hello <endofturn> world"
    assert normalize_text("hello <end-of-turn> world", eot_token="<end-of-turn>") == "hello <end-of-turn> world"
    # a literal "<eot>" in the text is not special when a different
    # eot_token is active
    assert normalize_text("hello <eot> world", eot_token="<endofturn>") == "hello world"


def test_normalize_text_strips_generic_tags():
    assert normalize_text("hello <afdaslk> world") == "hello world"
    assert normalize_text("<noise> hello <music> world <eot>") == "hello world"
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
    # kept, other tags (including "<eot>", no eot_token given here) stripped
    assert normalize_text(
        "hello <noise> world <eot> <music> bye", enable_special_tokens=["<noise>"]
    ) == "hello <noise> world bye"
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
    (proving a literal "<eot>" in the text is not special when a
    different eot_token is active), enable_special_tokens, letter
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
    test_normalize_text_eot_token_custom_marker_variants()
    test_normalize_text_strips_generic_tags()
    test_normalize_text_custom_eot_strips_other_tags_including_default()
    test_normalize_text_letter_folding()
    test_normalize_text_map_letters_override()
    test_normalize_text_enable_special_tokens()
    test_normalize_text_full()
    print("ok")
    test_normalize_text_tanwin_alif_folds_to_plain_alif()
    test_normalize_numbers_edge_connectors_survive()
    test_normalize_numbers_connector_only_span_is_not_zero()
    test_normalize_numbers_two_ones_joined_by_connector_are_a_list()
    test_normalize_numbers_case_insensitive_english()
    test_normalize_numbers_hamza_spelled_words()
    test_normalize_numbers_decomposed_unicode()
    test_normalize_numbers_separate_numbers_stay_separate()
    test_normalize_numbers_extended_arabic_indic_digits()
    test_normalize_text_persian_lookalike_letters_fold()
    test_normalize_text_presentation_forms_decompose()
    test_normalize_numbers_vowelled_number_words()
    test_normalize_numbers_plural_thousands()
