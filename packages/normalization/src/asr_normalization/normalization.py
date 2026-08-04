import re
import unicodedata
from typing import List

URDU_CHARS_PATTERN = re.compile(
    r'[؀-ؠً-ٟ٠-ٯٰ-ۿݐ-ݿࢠ-ࣿ]'
)
DIACRITICS_PATTERN = re.compile(r"[ؗ-ًؚ-ْـ]")
WHITESPACE_PATTERN = re.compile(r"\s+")

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
    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
    'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
    'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50,
    'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90
}
MULT_MAP = {
    'مائه': 100, 'مئة': 100, 'hundred': 100,
    'الف': 1000, 'ألف': 1000, 'thousand': 1000
}
SUM_CONNECTORS = {'و', 'and'}
ALL_NUM_WORDS = set(SINGLE_MAP.keys()) | set(TENS_MAP.keys()) | set(MULT_MAP.keys()) | SUM_CONNECTORS
WORDS_RP = r'\b(' + '|'.join(re.escape(k) for k in ALL_NUM_WORDS) + r')\b'
COMPOUND_NUM_PATTERN = re.compile(f'{WORDS_RP}(?:\\s+{WORDS_RP})*')
DIGIT_SPACER_PATTERN = re.compile(r'(\d)\s+(?=\d)')
# Thousands-grouped quantities, e.g. "100,000" or "1,234,567" — the comma is
# a formatting separator, not meaningful content; flatten to "100000".
THOUSANDS_SEPARATOR_PATTERN = re.compile(r'\d{1,3}(?:,\d{3})+')


def normalize_numbers(text: str) -> str:
    if not text:
        return ""

    # 3.1 Arabic-Indic digits → ASCII digits
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))

    # 3.2 Number word spans → digit strings
    def process_num_words(match):
        words = match.group(0).split()

        if len(words) == 1:
            w = words[0]
            for mapping in (SINGLE_MAP, TENS_MAP, MULT_MAP):
                if w in mapping:
                    return str(mapping[w])
            return w

        has_summing_clue = any(
            w in TENS_MAP or w in MULT_MAP or w in SUM_CONNECTORS
            for w in words
        )

        if has_summing_clue:
            total = 0
            current = 0
            for w in words:
                if w in SUM_CONNECTORS:
                    continue
                if w in SINGLE_MAP:
                    current += SINGLE_MAP[w]
                elif w in TENS_MAP:
                    current += TENS_MAP[w]
                elif w in MULT_MAP:
                    total += max(1, current) * MULT_MAP[w]
                    current = 0
            return str(total + current)
        else:
            return "".join(str(SINGLE_MAP[w]) for w in words if w in SINGLE_MAP)

    text = COMPOUND_NUM_PATTERN.sub(process_num_words, text)

    # 3.3 Collapse spaces between adjacent digits ("2 0 2 4" → "2024")
    text = DIGIT_SPACER_PATTERN.sub(r'\1', text)

    # 3.4 Flatten thousands-separator commas in quantities ("100,000" -> "100000").
    text = THOUSANDS_SEPARATOR_PATTERN.sub(lambda m: m.group(0).replace(",", ""), text)

    return text


# Matches "...", "..", and whitespace-spaced runs like ". . ." — but not two
# separate sentence-ending periods with actual words between them, since only
# whitespace (not arbitrary text) is allowed between the dots.
ELLIPSIS_PATTERN = re.compile(r"\.(?:\s*\.)+")


def normalize_text(text: str, enable_punc: List[str] = None, eot_token: str = None) -> str:
    if not text:
        return ""

    # Collapse "..." (any run of 2+ periods) to a single "." — an ellipsis
    # isn't a decimal point (single "." between digits is left untouched
    # further down), just a run-on/trailing-off marker.
    text = ELLIPSIS_PATTERN.sub(".", text)

    text = normalize_numbers(text)

    # Temporarily hide eot_token before normalization so it doesn't get stripped or separated
    if eot_token and eot_token in text:
        text = text.replace(eot_token, " __EOT_TOKEN__ ")

    # 1. Basic normalization
    text = text.lower()
    text = unicodedata.normalize("NFC", text)

    # Strip Urdu/Persian/Extended Arabic contamination, but spare any
    # character that's explicitly configured as keepable punctuation
    # (e.g. Arabic ؟ U+061F and ، U+060C fall inside this range too)
    if enable_punc:
        protected_punc = set(enable_punc)
        text = URDU_CHARS_PATTERN.sub(lambda m: m.group(0) if m.group(0) in protected_punc else "", text)
    else:
        text = URDU_CHARS_PATTERN.sub("", text)

    # 2. Arabic character normalization
    arabic_map = {
        "آ": "ا", "ٱ": "ا", "ٲ": "ا", "ٳ": "ا",
    }
    for src, tgt in arabic_map.items():
        text = text.replace(src, tgt)

    # 4. Remove diacritics and tatweel
    text = DIACRITICS_PATTERN.sub("", text)

    # 5. Remove punctuation / symbols
    if enable_punc:
        # Create a dynamic pattern that excludes enabled punctuation
        punc_to_keep = "".join(re.escape(p) for p in enable_punc)
        # Keep Arabic letters, a-z, 0-9, whitespace, apostrophes, AND enabled punctuation
        # (both straight ' and curly ’, so English contractions like "I'll"/"that's" survive)
        dynamic_pattern = re.compile(rf"[^ء-يa-z0-9\s{punc_to_keep}_'’]")  # include _ for __EOT_TOKEN__
        text = dynamic_pattern.sub(" ", text)
    else:
        # Keeps: Arabic letters, a-z, 0-9, space, and apostrophes (straight '
        # and curly ’) so contractions survive. Need to include _ for __EOT_TOKEN__
        temp_pattern = re.compile(r"[^ء-يa-z0-9\s_'’]")
        text = temp_pattern.sub(" ", text)

    # Re-insert eot_token
    if eot_token and " __eot_token__ " in text:
        text = text.replace(" __eot_token__ ", f" {eot_token} ")

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

    # Give eot_token exactly one space on both sides — it's a standalone
    # marker, not glued onto the preceding word/punctuation.
    if eot_token:
        escaped_eot = re.escape(eot_token)
        text = re.sub(r'\s*' + escaped_eot + r'\s*', f' {eot_token} ', text)

    # Strip a leading eot_token — a segment shouldn't start with an
    # end-of-turn marker.
    if eot_token:
        leading_eot_pattern = re.compile(r'^(?:\s*' + re.escape(eot_token) + r')+\s*')
        text = leading_eot_pattern.sub("", text)

    # 6. Normalize whitespace
    text = WHITESPACE_PATTERN.sub(" ", text).strip()

    return text
