import re
import unicodedata
from decimal import Decimal
from typing import Dict, List

URDU_CHARS_PATTERN = re.compile(
    r'[؀-ؠً-ٟ٠-ٯٰ-ۿݐ-ݿࢠ-ࣿ]'
)
DIACRITICS_PATTERN = re.compile(r"[ؗ-ًؚ-ْـ]")
WHITESPACE_PATTERN = re.compile(r"\s+")

# Hamza-variant folding: collapse alif-hamza forms to plain alif. Passed
# as the map_letters default below so callers can see exactly what's
# mapped and pass their own dict (e.g. {**MAP_LETTERS, "ة": "ه"}) to add,
# override, or drop entries.
MAP_LETTERS = {
    "أ": "ا", "إ": "ا",
    "آ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا",
}

# Number Conversion Maps
SINGLE_MAP = {
    'صفر': 0, 'واحد': 1, 'واحدة': 1, 'احد': 1, 'إحدى': 1, 'اثنان': 2, 'اثنين': 2, 'اثنتان': 2, 'اثنتين': 2, 'اثنا': 2, 'اثني': 2,
    'ثلاثه': 3, 'ثلاثة': 3, 'ثلاث': 3,
    'اربعه': 4, 'اربعة': 4, 'اربع': 4,
    'خمسه': 5, 'خمسة': 5, 'خمس': 5,
    'سته': 6, 'ستة': 6, 'ست': 6,
    'سبعه': 7, 'سبعة': 7, 'سبع': 7,
    'ثمانيه': 8, 'ثمانية': 8, 'ثمان': 8,
    'تسعه': 9, 'تسعة': 9, 'تسع': 9,
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9
}
TENS_MAP = {
    'عشره': 10, 'عشرة': 10, 'عشر': 10,
    'عشرون': 20, 'عشرين': 20,
    'ثلاثون': 30, 'ثلاثين': 30,
    'اربعون': 40, 'اربعين': 40,
    'خمسون': 50, 'خمسين': 50,
    'ستون': 60, 'ستين': 60,
    'سبعون': 70, 'سبعين': 70,
    'ثمانون': 80, 'ثمانين': 80,
    'تسعون': 90, 'تسعين': 90,
    # dialect fused teen suffix ("خمس طعش" = 15): behaves exactly like the
    # MSA spaced "عشر"/"عشره" (adds 10 to a preceding SINGLE_MAP word), so
    # it reuses that same summing logic below rather than needing a branch.
    'طعش': 10, 'طعشر': 10,
    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
    'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
    'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
    'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90
}
MULT_MAP = {
    'مائه': 100, 'مائة': 100, 'مئة': 100, 'مئه': 100, 'مية': 100, 'ميه': 100, 'hundred': 100,
    'الف': 1000, 'ألف': 1000, 'آلاف': 1000, 'الاف': 1000, 'ألاف': 1000, 'thousand': 1000,
    'مليون': 1_000_000, 'ملايين': 1_000_000, 'million': 1_000_000,
    'مليار': 1_000_000_000, 'مليارات': 1_000_000_000, 'billion': 1_000_000_000,
}
# Dual-inflected numbers are a single word carrying "two" already baked in
# ("الفين" = 2000), not a bare multiplier waiting for a multiplicand like
# MULT_MAP, so they get their own map and their own branch below.
DUAL_MAP = {
    'الفين': 2000, 'ألفين': 2000,
    'مئتين': 200, 'ميتين': 200, 'مائتين': 200,
}
# Glued hundred-compounds ("ثلاثمائة" = 300) are one fused word with no
# space, unlike "SINGLE + MULT" ("ثلاثة مائة" would be two words). Already a
# complete value like DUAL_MAP, not a bare multiplier. Generated from every
# ones-stem × hundred-spelling combination seen in real transcripts.
_HUNDREDS_ONES_STEMS = {
    'ثلاث': 3, 'تلت': 3, 'اربع': 4, 'أربع': 4, 'خمس': 5,
    'ست': 6, 'سبع': 7, 'ثمان': 8, 'تسع': 9,
}
_HUNDRED_SUFFIXES = ['مائة', 'مائه', 'مئة', 'مئه', 'مية', 'ميه']
GLUED_HUNDREDS_MAP = {
    stem + suffix: value * 100
    for stem, value in _HUNDREDS_ONES_STEMS.items()
    for suffix in _HUNDRED_SUFFIXES
}
# ── Spelling coverage ─────────────────────────────────────────────────────────
# normalize_numbers runs before normalize_text's letter fold, so every spelling
# a speaker's transcript can contain has to be a key here, or two spellings of
# the same number normalize differently ("أربعة" stayed a word, "اربعة" → 4).
SINGLE_MAP.update({
    # hamza spellings
    'أربعه': 4, 'أربعة': 4, 'أربع': 4,
    'إثنان': 2, 'إثنين': 2, 'أثنين': 2, 'إثنتان': 2, 'إثنتين': 2, 'إثنا': 2, 'إثني': 2,
    # MSA feminine / construct forms ("اثنتا عشرة", "ثماني عشرة")
    'اثنتا': 2, 'إثنتا': 2, 'ثماني': 8,
    # Egyptian
    'اتنين': 2, 'إتنين': 2, 'تلاتة': 3, 'تلاته': 3, 'تلات': 3,
    'تمانية': 8, 'تمانيه': 8, 'تمان': 8,
})
TENS_MAP.update({
    'أربعون': 40, 'أربعين': 40,
    'تلاتين': 30, 'تلاتون': 30, 'تمانين': 80, 'تمنين': 80,
    # Egyptian (-تاشر/-طاشر) and Levantine (-طعش) fused teens. They add like a
    # tens word, so "ميتين وخمستاشر" = 215 needs no special branch.
    'حداشر': 11, 'احداشر': 11, 'إحداشر': 11, 'حدعش': 11,
    'اتناشر': 12, 'اطناشر': 12, 'اثناشر': 12, 'طنعش': 12,
    'تلتاشر': 13, 'تلاتاشر': 13, 'تلطاشر': 13, 'تلطعش': 13,
    'اربعتاشر': 14, 'أربعتاشر': 14, 'اربعطاشر': 14, 'اربعطعش': 14,
    'خمستاشر': 15, 'خمسطاشر': 15, 'خمسطعش': 15,
    'ستاشر': 16, 'سطاشر': 16, 'سطعش': 16,
    'سبعتاشر': 17, 'سبعطاشر': 17, 'سبعطعش': 17,
    'تمنتاشر': 18, 'تمانتاشر': 18, 'تمنطاشر': 18, 'تمنطعش': 18,
    'تسعتاشر': 19, 'تسعطاشر': 19, 'تسعطعش': 19,
})
MULT_MAP.update({'تلاف': 1000, 'تالاف': 1000})
DUAL_MAP.update({
    # MSA nominative duals ("مئتان", "ألفان") alongside the genitive ones
    'مئتان': 200, 'مائتان': 200, 'ألفان': 2000, 'الفان': 2000,
    'مليونين': 2_000_000, 'مليونان': 2_000_000, 'مليارين': 2_000_000_000, 'ملياران': 2_000_000_000,
})
GLUED_HUNDREDS_MAP.update({
    stem + suffix: value * 100
    for stem, value in {'ربع': 4, 'تمن': 8, 'تمان': 8}.items()    # Egyptian "ربعمية", "تمنمية"
    for suffix in _HUNDRED_SUFFIXES
})

# ── Words that are only sometimes numbers ─────────────────────────────────────
# Plural multipliers count only right after a number ("ثلاثة آلاف" = 3000). On
# their own they mean "thousands of", not 1000: "آلاف الأشخاص" stays words.
PLURAL_MULTIPLIERS = {'آلاف', 'الاف', 'ألاف', 'تلاف', 'تالاف', 'ملايين', 'مليارات'}

# "one" words that far more often mean "someone" / "one of" / Sunday. Numeric
# only when a tens word follows: "أحد عشر" = 11, "إحدى وعشرين" = 21, but
# "لا أحد" and "إحدى المدارس" stay words. Includes و-fused forms, since
# splitting "وأحد" apart would change text that isn't a number at all.
BEFORE_TENS_ONLY = {'أحد': 1, 'احد': 1, 'إحدى': 1, 'احدى': 1, 'وأحد': 1, 'وإحدى': 1, 'واحدى': 1}

# Egyptian "تمن" (8) is also "price". Numeric only before a multiplier:
# "تمن تلاف" = 8000, "تمن مية" = 800.
BEFORE_MULT_ONLY = {'تمن': 8, 'وتمن': 8}

# Half/quarter count only right after "و" + a multiplier: "مليون ونص" = 1500000,
# "مية وربع" = 125. "الساعة خمسة ونص" (half past five) stays words.
FRACTIONS = {'نص': 0.5, 'نصف': 0.5, 'ربع': 0.25, 'ونص': 0.5, 'ونصف': 0.5, 'وربع': 0.25}

# Words that are numbers only when they aren't standing alone in one of these
# contexts. Each rule comes from a real transcript misfire and only looks at
# the neighbouring word, so a number with other number words around it is
# never affected ("مية وخمسين" is still 150).
#
# Egyptian "مية" is "water" at least as often as "hundred": alone, it's a word,
# unless a currency or unit follows ("مية جنيه", "مية درجة") or it's a
# percentage ("مية في المية" = 100%).
NEEDS_NUMBER_NEIGHBOUR = {'مية', 'ميه'}
UNIT_WORDS = {
    'جنيه', 'ريال', 'دولار', 'درهم', 'دينار', 'ليرة', 'يورو', 'درجة', 'درجه',
    'كيلو', 'جرام', 'جرامات', 'متر', 'كيلومتر', 'لتر', 'سنة', 'سنه', 'يوم', 'ساعة', 'ساعه',
    'دقيقة', 'دقيقه', 'ثانية', 'مرة', 'مره', 'شخص', 'نفر', 'طالب',
}
PERCENT_WORDS = {'المية', 'الميه', 'المائة', 'المئة'}
# ... or an amount word comes right before it ("حوالي مية", "دفعت مية").
AMOUNT_PREVIOUS_WORDS = {'حوالي', 'بحوالي', 'تقريبا', 'ب', 'دفعت', 'اكتر', 'اكثر', 'أكثر', 'اقل', 'أقل'}
# "ست البيت" / "كل ست بيت" = housewife, "ست الكل" = lady. A count takes an
# indefinite noun ("ست حاجات"), never a definite one.
LADY_WORDS = {'ست'}
# "السادس عشر" = sixteenth: the ordinal's "عشر" is not the number 10.
ORDINAL_PATTERN = re.compile(r'^ال(?:حادي|ثاني|ثالث|رابع|خامس|سادس|سابع|ثامن|تاسع)ة?$')
TENS_AFTER_ORDINAL = {'عشر', 'عشرة'}
# Fixed phrases, not quantities: "ألف عافية", "ألف مبروك", "شكرا مليون".
IDIOM_SCALES = {'ألف', 'الف', 'مليون'}
IDIOM_NEXT_WORDS = {'عافية', 'عافيه', 'سلامة', 'سلامه', 'مبروك', 'شكر', 'مرحبا', 'رحمة', 'رحمه'}
IDIOM_PREVIOUS_WORDS = {'شكرا', 'مرسي', 'thanks'}
# "كل واحد" = everyone, "واحدة من" = one of, "no one" / "one of".
PRONOUN_ONES = {'واحد', 'واحدة', 'one'}
PRONOUN_PREVIOUS_WORDS = {'كل', 'لكل', 'بكل', 'اي', 'أي', 'ولا', 'no', 'every', 'any', 'each', 'the'}
PRONOUN_NEXT_WORDS = {'من', 'منهم', 'منهن', 'منكم', 'منا', 'فينا', 'فيهم', 'of'}

for _word in BEFORE_TENS_ONLY:
    SINGLE_MAP.pop(_word, None)   # "احد"/"إحدى" used to convert on their own

SUM_CONNECTORS = {'و', 'and'}
ALL_NUM_WORDS = (
    set(SINGLE_MAP.keys()) | set(TENS_MAP.keys()) | set(MULT_MAP.keys())
    | set(DUAL_MAP.keys()) | set(GLUED_HUNDREDS_MAP.keys()) | SUM_CONNECTORS
    | set(BEFORE_TENS_ONLY) | set(BEFORE_MULT_ONLY) | set(FRACTIONS)
)
# A digit string is part of a span only when a multiplier word follows it, so
# "5 مليون" and "11 ألف وتسعة وتسعين" parse as one number (5000000, 11099)
# while ordinary digits elsewhere are never touched.
_SCALE_WORDS = sorted((w for w, m in MULT_MAP.items() if m >= 1000), key=len, reverse=True)
_DIGITS_BEFORE_SCALE = (
    r'(?<![\d.])\d+(?:\.\d+)?(?=\s+(?:' + '|'.join(re.escape(w) for w in _SCALE_WORDS) + r')\b)'
)
WORDS_RP = r'(\b(?:' + '|'.join(re.escape(k) for k in ALL_NUM_WORDS) + r')\b|' + _DIGITS_BEFORE_SCALE + ')'
# IGNORECASE: this runs before normalize_text lowercases, so "One hundred"
# used to come out as "one 100" and "FIVE" was never converted.
COMPOUND_NUM_PATTERN = re.compile(f'{WORDS_RP}(?:\\s+{WORDS_RP})*', re.IGNORECASE)
# Joins digits spelled out one at a time ("2 0 2 4" → "2024"): a run of three or
# more lone digits. Separate numbers stay separate ("2020 3" used to become
# "20203"), and so does a two-digit range ("3 4" = three or four, not 34).
DIGIT_SPACER_PATTERN = re.compile(r'(?<![\d.,])\d(?:\s+\d(?![\d.,])){2,}')
# Thousands-grouped quantities, e.g. "100,000" or "1,234,567" — the comma is
# a formatting separator, not meaningful content; flatten to "100000".
# Anchored on both sides so a comma between two separate numbers isn't read as
# a separator ("2019,2020" used to become "20192020"). A trailing punctuation
# comma still works ("100,000, then").
THOUSANDS_SEPARATOR_PATTERN = re.compile(r'(?<!\d)(?<!\d,)\d{1,3}(?:,\d{3})+(?!\d|,\d)')

# Arabic "and" (و) is often written glued to the next number word with no
# space ("وعشرين"), so Python's \b never fires between them (both are \w)
# and COMPOUND_NUM_PATTERN can't see the connector at all. Split a leading
# fused و off any word it's immediately attached to, iff that word is a
# recognized number word, before compound matching runs.
# Never split a word that is itself a number word starting with و: "واحد" is
# "one", not "و" + "احد".
# Context-only, plural and fraction words are left glued: splitting "وآلاف"
# or "وأحد" changes the text even when they turn out not to be numbers.
_WAW_TARGET_WORDS = sorted(
    ALL_NUM_WORDS - SUM_CONNECTORS - set(BEFORE_TENS_ONLY) - set(BEFORE_MULT_ONLY)
    - PLURAL_MULTIPLIERS - set(FRACTIONS),
    key=len, reverse=True,
)
_WAW_WHOLE_WORDS = sorted((w for w in _WAW_TARGET_WORDS if w.startswith('و')), key=len, reverse=True)
FUSED_WAW_PATTERN = re.compile(
    r'(?<!\S)(?!(?:' + '|'.join(re.escape(w) for w in _WAW_WHOLE_WORDS) + r')\b)'
    r'و(?=(?:' + '|'.join(re.escape(w) for w in _WAW_TARGET_WORDS) + r')\b)'
)

# Tanwin fathah (ً) on a carrier alif at a word's end, in either codepoint
# order ("شكراً" alif-then-mark, "شكرًا" mark-then-alif). The alif+mark pair
# is just another alif variant, so it folds to a plain ا like أ/إ/آ do in
# MAP_LETTERS: "شكراً" → "شكرا", "جداً" → "جدا".
#
# Only a number word also drops the carrier alif, because the alif isn't part
# of its map key ("أربعاً" → "أربع", which then matches). Deleting the alif
# unconditionally used to truncate every ordinary word: "شكراً" → "شكر".
TANWIN_ALIF_PATTERN = re.compile(r'([ء-ي]+)(?:اً|ًا)')
TANWIN_FATHA_PATTERN = re.compile(r'ً')

# Every other diacritic and tatweel (DIACRITICS_PATTERN minus U+064B). Stripped
# before number matching: a combining mark after a number word ends the regex
# word there, so "ألفٍ وسبعمائة وثلاثة وتسعين" split into "1000 793" instead
# of 1793. U+064B stays until the tanwin-alif fold below has used it.
DIACRITICS_EXCEPT_FATHATAN_PATTERN = re.compile(r'[\u0617-\u061A\u064C-\u0652\u0640]')

# Arabic-Indic (٠-٩) and Extended Arabic-Indic / Persian (۰-۹) digits.
# Also the Arabic decimal (٫) and thousands (٬) separators.
ARABIC_DIGITS = str.maketrans({
    **dict(zip("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)), "٫": ".", "٬": ",",
})

# Arabic presentation forms (ﻻ, ﷲ, ﷺ, contextual shapes like ﻣﺮﺣﺒﺎ) are
# compatibility encodings of ordinary letters. NFKC turns them back; without it
# they fell through to the symbol strip and were deleted, whole words included.
# U+FEFF (BOM) excluded: it has no letter to decompose to.
PRESENTATION_FORMS_PATTERN = re.compile(r'[\uFB50-\uFDFF\uFE70-\uFEFC]+')

# Persian/Urdu codepoints that render identically to an Arabic letter, common
# from Persian keyboard layouts. Folded rather than stripped: the Urdu/Persian
# strip used to delete them mid-word ("کتاب یوم" → "تاب وم").
LOOKALIKE_LETTERS = str.maketrans({
    "ی": "ي", "ک": "ك", "ە": "ه", "ھ": "ه", "ہ": "ه", "ۃ": "ة",
})


# Lookup-only hamza fold: number-word keys are spelled with bare alif
# ("اربع"), but this runs before normalize_text's own letter fold.
_HAMZA_FOLD_FOR_LOOKUP = str.maketrans(MAP_LETTERS)


def _is_number_stem(stem):
    return stem in ALL_NUM_WORDS or stem.translate(_HAMZA_FOLD_FOR_LOOKUP) in ALL_NUM_WORDS


def _fold_tanwin_alif(match):
    stem = match.group(1)
    # also a number word behind a fused و ("وألفاً"): the و split runs after this
    if _is_number_stem(stem) or (stem.startswith('و') and _is_number_stem(stem[1:])):
        return stem
    return stem + 'ا'


CONTEXT_PUNCTUATION_PATTERN = re.compile(r'[^\w]')


def _classify_number_words(words, before="", after=()):
    """Per word of a matched span: True if it belongs to a number, else text.

    `before` is the word just before the span and `after` the (up to two) words
    just after it, for the context rules.
    """
    def neighbour(i, step):
        j = i + step
        while 0 <= j < len(words) and words[j] in SUM_CONNECTORS:
            j += step
        return j if 0 <= j < len(words) else None

    numeric = [False] * len(words)
    for i, w in enumerate(words):
        if w in SUM_CONNECTORS:
            continue
        if w[0].isdigit():
            numeric[i] = True       # only matched when a multiplier follows
            continue
        nxt, prv = neighbour(i, 1), neighbour(i, -1)
        if w in BEFORE_TENS_ONLY:
            numeric[i] = nxt is not None and words[nxt] in TENS_MAP
        elif w in BEFORE_MULT_ONLY:
            numeric[i] = nxt is not None and words[nxt] in MULT_MAP
        elif w in FRACTIONS:
            joined_by_waw = w.startswith('و') or (i >= 2 and words[i - 1] == 'و')
            numeric[i] = (joined_by_waw and prv is not None and numeric[prv]
                          and (words[prv] in MULT_MAP or words[prv] in DUAL_MAP))
        elif w in PLURAL_MULTIPLIERS:
            numeric[i] = i > 0 and numeric[i - 1]
        else:
            numeric[i] = True

    # Context rules, only for a word with no number word next to it in the span.
    for i, w in enumerate(words):
        if not numeric[i] or w in SUM_CONNECTORS:
            continue
        nxt, prv = neighbour(i, 1), neighbour(i, -1)
        if (nxt is not None and numeric[nxt]) or (prv is not None and numeric[prv]):
            continue
        prev_word = words[i - 1] if i > 0 else before
        following = list(words[i + 1:i + 3]) + list(after)
        next_word = following[0] if following else ""
        if w in NEEDS_NUMBER_NEIGHBOUR:
            numeric[i] = next_word in UNIT_WORDS or prev_word in AMOUNT_PREVIOUS_WORDS or (
                next_word == 'في' and len(following) > 1 and following[1] in PERCENT_WORDS)
        elif w in LADY_WORDS and (next_word.startswith('ال') or next_word == 'بيت'):
            numeric[i] = False
        elif w in TENS_AFTER_ORDINAL and ORDINAL_PATTERN.match(prev_word):
            numeric[i] = False
        elif w in IDIOM_SCALES and (next_word in IDIOM_NEXT_WORDS or prev_word in IDIOM_PREVIOUS_WORDS):
            numeric[i] = False
        elif w in PRONOUN_ONES and (prev_word in PRONOUN_PREVIOUS_WORDS or next_word in PRONOUN_NEXT_WORDS):
            numeric[i] = False

    # A connector joins a number only between two number words, and never
    # between two bare ones: "ثلاثة و اربعة" is a list ("3 و 4"), not 7.
    for i, w in enumerate(words):
        if w in SUM_CONNECTORS and 0 < i < len(words) - 1 and numeric[i - 1] and numeric[i + 1]:
            numeric[i] = not (words[i - 1] in SINGLE_MAP and words[i + 1] in SINGLE_MAP)
    # A fraction whose و was just ruled out isn't part of the number either.
    for i, w in enumerate(words):
        if w in FRACTIONS and not w.startswith('و') and numeric[i] and not numeric[i - 1]:
            numeric[i] = False
    return numeric


def _words_to_number(words):
    """Scale-based value of one number span ("خمسة وعشرين ألف" → 25000).

    Keeps three registers: `total` (finished thousands/millions/billions
    groups), `hundreds` and `below` (units + tens) of the group being built. A
    multiplier closes the group, so everything said before "ألف" is multiplied
    together, not just the last word ("ثلاثمائة وخمسين ألف" = 350000, not 50300).
    """
    total = hundreds = below = 0
    last_scale = 0      # last thousands-or-bigger multiplier applied to total
    last_mult = 0       # last multiplier of any size, for "ونص"/"وربع"
    for w in words:
        if w in SUM_CONNECTORS:
            continue
        if w[0].isdigit():
            below += Decimal(w)
            continue
        if w in FRACTIONS:
            part = int(last_mult * FRACTIONS[w])
            if last_mult >= 1000:
                total += part
            else:
                below += part
            continue
        if w in MULT_MAP:
            m = last_mult = MULT_MAP[w]
            if m == 100:
                hundreds += max(1, below) * 100
                below = 0
                continue
            group = hundreds + below
            if group == 0 and total and m > last_scale:
                total *= m                      # "ألف مليون" = 10**9
            else:
                total += max(1, group) * m
            hundreds = below = 0
            last_scale = m
            continue
        if w in DUAL_MAP:
            v = DUAL_MAP[w]
            if v >= 1000:
                total += v
                last_scale = last_mult = v // 2
            else:
                hundreds += v
                last_mult = 100
            continue
        if w in GLUED_HUNDREDS_MAP:
            hundreds += GLUED_HUNDREDS_MAP[w]
            last_mult = 100
            continue
        for mapping in (SINGLE_MAP, TENS_MAP, BEFORE_TENS_ONLY, BEFORE_MULT_ONLY):
            if w in mapping:
                below += mapping[w]
                break
    return total + hundreds + below


def _convert_number_run(run):
    if len(run) > 1 and all(w in SINGLE_MAP for w in run):
        digits = [str(SINGLE_MAP[w]) for w in run]
        # Two bare ones are a spoken range ("تلات أربع حبات" = 3 or 4, not 34);
        # three or more are read out digit by digit ("صفر واحد اتنين" = 012).
        return " ".join(digits) if len(run) == 2 else "".join(digits)
    value = Decimal(_words_to_number(run))
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), 'f')     # "2.75 ألف" is 2750, "0.0005 ألف" is 0.5


def normalize_numbers(text: str) -> str:
    """Convert Arabic-Indic digits and Arabic/English number words to digit strings.

    Handles: chained multipliers as a product ("مائة ألف" → 100000, not
    1100), a fused leading و connector ("وعشرين" → treated as "و عشرين"),
    dual-inflected hundreds/thousands ("الفين", "مئتين"), glued
    hundred-compounds ("ثلاثمائة" → 300), million/billion, the colloquial
    "مية"/"ميه"/"مئه" hundred spellings, dialect fused teens ("خمس طعش" →
    15), and tanwin-carrier alifs on number words ("أربعاً"). Tanwin on any
    other word folds to a plain alif ("شكراً" → "شكرا"), never truncates it.
    Diacritics and tatweel are stripped from the whole text first, so fully
    vowelled number words ("ألفٍ", "خمسةٍ") match like bare ones.

    Values are built scale by scale (see _words_to_number), so a compound
    before a multiplier is multiplied as a whole: "خمسة وعشرين ألف" = 25000,
    "ثلاثمائة وخمسين ألف" = 350000. Also covers MSA nominative duals
    ("مئتان", "ألفان"), Egyptian and Levantine spellings ("تلاتة", "اتناشر",
    "ربعمية", "تلات تلاف"), a digit string before a multiplier ("3.5 مليون"),
    and "ونص"/"وربع" after a multiplier ("مليون ونص").

    Does not handle fractions anywhere else ("خمسة ونص" stays words, it's
    usually a time), ordinals ("الثالث"), or words that are numbers only in some
    contexts beyond the ones listed in BEFORE_TENS_ONLY/BEFORE_MULT_ONLY
    ("واحد" meaning "someone" still converts).

    Args:
        text: input string.

    Returns:
        text with digits/number-words normalized to ASCII digit strings.
    """
    if not text:
        return ""

    # Composed form first: a decomposed hamza (ا + U+0654) can't match a
    # number-word key or the tanwin pattern below.
    text = unicodedata.normalize("NFC", text)

    # 3.1 Arabic-Indic and Extended Arabic-Indic digits → ASCII digits
    text = text.translate(ARABIC_DIGITS)

    # 3.1b Diacritics off, then the tanwin-carrier alif folded to a plain alif
    # ("شكراً" → "شكرا"), or dropped on a number word ("أربعاً" → "أربع"),
    # before word matching; and fused و ("وعشرين" → "و عشرين") before
    # compound matching.
    text = DIACRITICS_EXCEPT_FATHATAN_PATTERN.sub('', text)
    text = TANWIN_ALIF_PATTERN.sub(_fold_tanwin_alif, text)
    text = TANWIN_FATHA_PATTERN.sub('', text)
    text = FUSED_WAW_PATTERN.sub('و ', text)

    # 3.2 Number word spans → digit strings
    def process_num_words(match):
        original = match.group(0).split()
        words = [w.lower() for w in original]
        before = match.string[:match.start()].split()
        after = match.string[match.end():].split()
        before = CONTEXT_PUNCTUATION_PATTERN.sub('', before[-1]).lower() if before else ""
        after = [CONTEXT_PUNCTUATION_PATTERN.sub('', w).lower() for w in after[:2]]
        out, run = [], []
        for word, orig, is_number in zip(words, original, _classify_number_words(words, before, after)):
            if is_number:
                run.append(word)
                continue
            if run:
                out.append(_convert_number_run(run))
                run = []
            out.append(orig)
        if run:
            out.append(_convert_number_run(run))
        return " ".join(out)

    text = COMPOUND_NUM_PATTERN.sub(process_num_words, text)

    # 3.3 Collapse spaces between adjacent digits ("2 0 2 4" → "2024")
    text = DIGIT_SPACER_PATTERN.sub(lambda m: WHITESPACE_PATTERN.sub('', m.group(0)), text)

    # 3.4 Flatten thousands-separator commas in quantities ("100,000" -> "100000").
    text = THOUSANDS_SEPARATOR_PATTERN.sub(lambda m: m.group(0).replace(",", ""), text)

    return text


# Matches "...", "..", and whitespace-spaced runs like ". . ." — but not two
# separate sentence-ending periods with actual words between them, since only
# whitespace (not arbitrary text) is allowed between the dots.
ELLIPSIS_PATTERN = re.compile(r"\.(?:\s*\.)+")

# Matches any "<...>" tag span (brackets + contents), e.g. "<afdaslk>",
# "<noise>". Doesn't match nested/malformed brackets like "<<eot>>" past
# the first ">", which is fine, real transcript tags aren't nested.
TAG_PATTERN = re.compile(r"<[^<>]*>")

# A "." that isn't a decimal point. The punctuation strip keeps dots and then
# removes only these, so "3.5" survives even when "." isn't enabled punctuation
# (it used to become "3 5", a different number).
NON_DECIMAL_DOT_PATTERN = re.compile(r"(?<!\d)\.|\.(?!\d)")


def normalize_text(
    text: str,
    enable_punc: List[str] = None,
    eot_token: str = None,
    enable_special_tokens: List[str] = None,
    map_letters: Dict[str, str] = MAP_LETTERS,
) -> str:
    """Normalize Arabic/English ASR transcript text.

    Args:
        text: input string to normalize.
        enable_punc: punctuation characters to keep (e.g. ["?", ","])
            instead of stripping all punctuation; spacing is normalized
            around each one kept. None (default) strips all punctuation.
        eot_token: end-of-turn marker to protect through normalization,
            e.g. "<eot>", "<endofturn>", "<end-of-turn>", whatever your
            model actually emits. Kept intact, given exactly one space on
            both sides, and stripped if it ends up leading the string.
            None (default): no eot marker is protected, a literal "<eot>"
            in the text is just another tag and gets stripped like any
            other "<...>" span.
        enable_special_tokens: extra "<...>" tokens (e.g. ["<noise>",
            "<music>"]) to keep intact, on top of the active eot marker.
            Kept literally, unlowercased, wrapped in single spaces after
            whitespace collapsing; unlike eot_token they get no
            leading-strip treatment.
        map_letters: letter-fold mapping, defaults to MAP_LETTERS above so
            you can see exactly what's mapped. Pass your own dict to add
            to it, override an entry, or drop one, e.g.
            {**MAP_LETTERS, "ة": "ه"} to add a mapping on top of the
            default, or a filtered copy to remove one.

    Returns:
        Normalized text. Any "<...>" tag span (e.g. "<afdaslk>",
        "<noise>") is stripped entirely, brackets and contents, except
        eot_token (if given) and any enable_special_tokens.
    """
    if not text:
        return ""

    active_eot = eot_token
    special_tokens = list(enable_special_tokens or [])

    # Collapse "..." (any run of 2+ periods) to a single "." — an ellipsis
    # isn't a decimal point (single "." between digits is left untouched
    # further down), just a run-on/trailing-off marker.
    text = ELLIPSIS_PATTERN.sub(".", text)

    # Before number matching, so "اثنین" (Persian ی) and "ﺛﻼﺛﺔ" convert too.
    text = PRESENTATION_FORMS_PATTERN.sub(lambda m: unicodedata.normalize("NFKC", m.group(0)), text)
    text = text.translate(LOOKALIKE_LETTERS)

    text = normalize_numbers(text)

    # Temporarily hide the eot token and any enabled special tokens before
    # normalization so they don't get stripped or separated, then strip
    # every other "<...>" tag span outright (brackets and contents) before
    # it can leak letters like "<afdaslk>" -> "afdaslk" through the
    # character-class punctuation step further down.
    if active_eot and active_eot in text:
        text = text.replace(active_eot, " __EOT_TOKEN__ ")
    for i, token in enumerate(special_tokens):
        if token in text:
            text = text.replace(token, f" __SPECIAL_TOKEN_{i}__ ")
    text = TAG_PATTERN.sub("", text)

    # 1. Basic normalization
    text = text.lower()
    text = unicodedata.normalize("NFC", text)

    # Strip Urdu/Persian/Extended Arabic contamination, but spare any
    # character that's explicitly configured as keepable punctuation
    # (e.g. Arabic ؟ U+061F and ، U+060C fall inside this range too), and
    # any map_letters source character -- some hamza variants (ٱ ٲ ٳ,
    # U+0671-0673) fall inside this same ٰ-ۿ strip range, so
    # without this they're deleted here before the fold step below ever
    # sees them, instead of being folded like the map promises.
    protected_chars = set(enable_punc or []) | set(map_letters)
    if protected_chars:
        text = URDU_CHARS_PATTERN.sub(lambda m: m.group(0) if m.group(0) in protected_chars else "", text)
    else:
        text = URDU_CHARS_PATTERN.sub("", text)

    # 2. Arabic character normalization
    for src, tgt in map_letters.items():
        text = text.replace(src, tgt)

    # 4. Remove diacritics and tatweel
    text = DIACRITICS_PATTERN.sub("", text)

    # 5. Remove punctuation / symbols
    if enable_punc:
        # Create a dynamic pattern that excludes enabled punctuation
        punc_to_keep = "".join(re.escape(p) for p in enable_punc)
        # Keep Arabic letters, a-z, 0-9, whitespace, apostrophes, AND enabled punctuation
        # (both straight ' and curly ’, so English contractions like "I'll"/"that's" survive)
        dynamic_pattern = re.compile(rf"[^ء-يa-z0-9\s{punc_to_keep}_'’.]")  # include _ for __EOT_TOKEN__
        text = dynamic_pattern.sub(" ", text)
        if "." not in enable_punc:
            text = NON_DECIMAL_DOT_PATTERN.sub(" ", text)
    else:
        # Keeps: Arabic letters, a-z, 0-9, space, and apostrophes (straight '
        # and curly ’) so contractions survive. Need to include _ for __EOT_TOKEN__
        temp_pattern = re.compile(r"[^ء-يa-z0-9\s_'’.]")
        text = temp_pattern.sub(" ", text)
        text = NON_DECIMAL_DOT_PATTERN.sub(" ", text)

    # Re-insert eot_token
    if active_eot and " __eot_token__ " in text:
        text = text.replace(" __eot_token__ ", f" {active_eot} ")

    # Re-insert special tokens
    for i, token in enumerate(special_tokens):
        placeholder = f" __special_token_{i}__ "
        if placeholder in text:
            text = text.replace(placeholder, f" {token} ")

    # Standardize spacing around enabled punctuation: no space before (glued
    # to the preceding word, standard writing convention), exactly one space
    # after — except a decimal/thousands separator (digit.digit / digit,digit)
    # which must stay tight ("1.6" not "1. 6").
    if enable_punc:
        for p in enable_punc:
            escaped_p = re.escape(p)
            # Remove space before punctuation
            text = re.sub(r'\s+' + escaped_p, p, text)
            # Add exactly one space after punctuation, except when it's a
            # decimal separator (digit.digit / digit,digit)
            if p in ('.', ','):
                def _add_space(m, _p=p):
                    i = m.start()
                    prev_digit = i > 0 and text[i - 1].isdigit()
                    next_digit = i + 1 < len(text) and text[i + 1].isdigit()
                    if prev_digit and next_digit:
                        return _p
                    return f'{_p} '
                text = re.sub(escaped_p + r'(?=[^\s])', _add_space, text)
            else:
                text = re.sub(escaped_p + r'(?=[^\s])', f'{p} ', text)

    # Strip any enabled punctuation stranded at the very start of the string
    # (e.g. a stray "،" or "." leading a transcript) — a sentence shouldn't
    # begin with terminal/connector punctuation.
    if enable_punc:
        leading_punc_pattern = re.compile(
            r'^(?:\s*[' + re.escape("".join(enable_punc)) + r'])+\s*'
        )
        text = leading_punc_pattern.sub("", text)

    if active_eot:
        # Give eot_token exactly one space on both sides — it's a
        # standalone marker, not glued onto the preceding word/punctuation.
        escaped_eot = re.escape(active_eot)
        text = re.sub(r'\s*' + escaped_eot + r'\s*', f' {active_eot} ', text)

        # Strip a leading eot_token — a segment shouldn't start with an
        # end-of-turn marker. Exception: if the eot marker is the *entire*
        # content (nothing else was ever said), keep one copy instead of
        # collapsing to an empty string, an empty-turn prediction is still
        # meaningful signal, not equivalent to no output at all.
        leading_eot_pattern = re.compile(r'^(?:\s*' + re.escape(active_eot) + r')+\s*')
        if leading_eot_pattern.fullmatch(text):
            text = active_eot
        else:
            text = leading_eot_pattern.sub("", text)

    # 6. Normalize whitespace
    text = WHITESPACE_PATTERN.sub(" ", text).strip()

    return text
