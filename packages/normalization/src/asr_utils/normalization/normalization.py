import re
import unicodedata
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
    'الف': 1000, 'ألف': 1000, 'thousand': 1000,
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
SUM_CONNECTORS = {'و', 'and'}
ALL_NUM_WORDS = (
    set(SINGLE_MAP.keys()) | set(TENS_MAP.keys()) | set(MULT_MAP.keys())
    | set(DUAL_MAP.keys()) | set(GLUED_HUNDREDS_MAP.keys()) | SUM_CONNECTORS
)
WORDS_RP = r'\b(' + '|'.join(re.escape(k) for k in ALL_NUM_WORDS) + r')\b'
COMPOUND_NUM_PATTERN = re.compile(f'{WORDS_RP}(?:\\s+{WORDS_RP})*')
DIGIT_SPACER_PATTERN = re.compile(r'(\d)\s+(?=\d)')
# Thousands-grouped quantities, e.g. "100,000" or "1,234,567" — the comma is
# a formatting separator, not meaningful content; flatten to "100000".
THOUSANDS_SEPARATOR_PATTERN = re.compile(r'\d{1,3}(?:,\d{3})+')

# Arabic "and" (و) is often written glued to the next number word with no
# space ("وعشرين"), so Python's \b never fires between them (both are \w)
# and COMPOUND_NUM_PATTERN can't see the connector at all. Split a leading
# fused و off any word it's immediately attached to, iff that word is a
# recognized number word, before compound matching runs.
_WAW_TARGET_WORDS = sorted((ALL_NUM_WORDS - SUM_CONNECTORS), key=len, reverse=True)
FUSED_WAW_PATTERN = re.compile(
    r'(?<!\S)و(?=(?:' + '|'.join(re.escape(w) for w in _WAW_TARGET_WORDS) + r')\b)'
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


# Lookup-only hamza fold: number-word keys are spelled with bare alif
# ("اربع"), but this runs before normalize_text's own letter fold.
_HAMZA_FOLD_FOR_LOOKUP = str.maketrans(MAP_LETTERS)


def _fold_tanwin_alif(match):
    stem = match.group(1)
    if stem in ALL_NUM_WORDS or stem.translate(_HAMZA_FOLD_FOR_LOOKUP) in ALL_NUM_WORDS:
        return stem
    return stem + 'ا'


def normalize_numbers(text: str) -> str:
    """Convert Arabic-Indic digits and Arabic/English number words to digit strings.

    Handles: chained multipliers as a product ("مائة ألف" → 100000, not
    1100), a fused leading و connector ("وعشرين" → treated as "و عشرين"),
    dual-inflected hundreds/thousands ("الفين", "مئتين"), glued
    hundred-compounds ("ثلاثمائة" → 300), million/billion, the colloquial
    "مية"/"ميه"/"مئه" hundred spellings, dialect fused teens ("خمس طعش" →
    15), and tanwin-carrier alifs on number words ("أربعاً"). Tanwin on any
    other word folds to a plain alif ("شكراً" → "شكرا"), never truncates it.

    Known unresolved edge case: a glued hundred-compound followed by "و" +
    tens, then a multiplier ("ثلاثمائة وخمسين ألف", want 350000) computes
    50300 instead — the tens gets multiplied alone instead of combined with
    the hundred first. Rare in practice (~8 hits across a 115k-line, two-
    dataset benchmark corpus); a linear single-pass parser can't resolve
    this without breaking "ميتين و سبع مية" (900, correctly handled), which
    needs the opposite treatment of the same connector. Needs real lookahead
    to fix properly, not attempted here.

    Does not handle fraction/half words ("نص", "ربع") or Levantine forms not
    covered above, they're left as plain words.

    Args:
        text: input string.

    Returns:
        text with digits/number-words normalized to ASCII digit strings.
    """
    if not text:
        return ""

    # 3.1 Arabic-Indic digits → ASCII digits
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))

    # 3.1b Tanwin-carrier alif folded to a plain alif ("شكراً" → "شكرا"), or
    # dropped on a number word ("أربعاً" → "أربع") before word matching, and
    # fused و ("وعشرين" → "و عشرين") before compound matching.
    text = TANWIN_ALIF_PATTERN.sub(_fold_tanwin_alif, text)
    text = TANWIN_FATHA_PATTERN.sub('', text)
    text = FUSED_WAW_PATTERN.sub('و ', text)

    # 3.2 Number word spans → digit strings
    def process_num_words(match):
        words = match.group(0).split()

        if len(words) == 1:
            w = words[0]
            for mapping in (SINGLE_MAP, TENS_MAP, MULT_MAP, DUAL_MAP, GLUED_HUNDREDS_MAP):
                if w in mapping:
                    return str(mapping[w])
            return w

        has_summing_clue = any(
            w in TENS_MAP or w in MULT_MAP or w in SUM_CONNECTORS or w in DUAL_MAP or w in GLUED_HUNDREDS_MAP
            for w in words
        )

        if has_summing_clue:
            total = 0
            current = 0
            pending_mult = 1  # accumulates a chain of adjacent MULT words,
            # e.g. "مائة ألف" (hundred thousand) → 100*1000, flushed as one
            # unit once a new segment starts.
            # SINGLE/TENS/DUAL/GLUED_HUNDREDS all just contribute a value to
            # the current segment ("ثلاثمائة وخمسين ألف" needs 300+50=350
            # combined into current *before* "ألف" multiplies the whole
            # thing to 350000, not 300 flushed away immediately and only the
            # trailing 50 getting multiplied).
            for w in words:
                if w in SUM_CONNECTORS:
                    # a connector between two bare multipliers means they're
                    # separate additive terms ("ألف ومئة" = 1000+100), not a
                    # chain, so it forces the same flush a new segment does.
                    if current or pending_mult != 1:
                        total += max(1, current) * pending_mult
                        current, pending_mult = 0, 1
                    continue
                if w in MULT_MAP:
                    # chain instead of flushing immediately, so "خمسة مائة
                    # ألف" (five hundred thousand) multiplies all three
                    # together (500000) instead of only the first (500).
                    pending_mult *= MULT_MAP[w]
                    continue
                for mapping in (SINGLE_MAP, TENS_MAP, DUAL_MAP, GLUED_HUNDREDS_MAP):
                    if w in mapping:
                        if pending_mult != 1:
                            total += max(1, current) * pending_mult
                            current, pending_mult = 0, 1
                        current += mapping[w]
                        break
            if current or pending_mult != 1:
                total += max(1, current) * pending_mult
            return str(total)
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

# Matches any "<...>" tag span (brackets + contents), e.g. "<afdaslk>",
# "<noise>". Doesn't match nested/malformed brackets like "<<eot>>" past
# the first ">", which is fine, real transcript tags aren't nested.
TAG_PATTERN = re.compile(r"<[^<>]*>")


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
        dynamic_pattern = re.compile(rf"[^ء-يa-z0-9\s{punc_to_keep}_'’]")  # include _ for __EOT_TOKEN__
        text = dynamic_pattern.sub(" ", text)
    else:
        # Keeps: Arabic letters, a-z, 0-9, space, and apostrophes (straight '
        # and curly ’) so contractions survive. Need to include _ for __EOT_TOKEN__
        temp_pattern = re.compile(r"[^ء-يa-z0-9\s_'’]")
        text = temp_pattern.sub(" ", text)

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
