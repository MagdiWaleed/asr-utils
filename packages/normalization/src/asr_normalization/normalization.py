import re
import unicodedata
from typing import List

ARABIC_NUM_PATTERN    = re.compile(r'[٠-٩]')
DIACRITICS_PATTERN    = re.compile(r'[ؗ-ًؚ-ْـ]')
CLEAN_PUNC_PATTERN    = re.compile(r'[^ء-يa-z0-9\s]')
URDU_CHARS_PATTERN    = re.compile(
    r'[؀-ؠً-ٟ٠-ٯٰ-ۿݐ-ݿࢠ-ࣿ]'
)
WHITESPACE_PATTERN    = re.compile(r'\s+')

SINGLE_MAP = {
    'صفر':0, 'واحد':1, 'واحدة':1, 'احد':1, 'إحدى':1,
    'اثنان':2, 'اثنين':2, 'اثنتان':2, 'اثنتين':2, 'اثنا':2, 'اثني':2,
    'ثلاثه':3, 'ثلاثة':3, 'ثلاث':3, 'اربعه':4, 'اربعة':4, 'اربع':4,
    'خمسه':5, 'خمسة':5, 'خمس':5, 'سته':6, 'ستة':6, 'ست':6,
    'سبعه':7, 'سبعة':7, 'سبع':7, 'ثمانيه':8, 'ثمانية':8, 'ثمان':8,
    'تسعه':9, 'تسعة':9, 'تسع':9,
    'zero':0, 'one':1, 'two':2, 'three':3, 'four':4, 'five':5,
    'six':6, 'seven':7, 'eight':8, 'nine':9,
}
TENS_MAP = {
    'عشره':10, 'عشرة':10, 'عشر':10, 'عشرون':20, 'عشرين':20,
    'ثلاثون':30, 'ثلاثين':30, 'اربعون':40, 'اربعين':40,
    'خمسون':50, 'خمسين':50, 'ستون':60, 'ستين':60,
    'سبعون':70, 'سبعين':70, 'ثمانون':80, 'ثمانين':80,
    'تسعون':90, 'تسعين':90,
    'ten':10, 'eleven':11, 'twelve':12, 'thirteen':13, 'fourteen':14,
    'fifteen':15, 'sixteen':16, 'seventeen':17, 'eighteen':18, 'nineteen':19,
    'twenty':20, 'thirty':30, 'forty':40, 'fifty':50,
    'sixty':60, 'seventy':70, 'eighty':80, 'ninety':90,
}
MULT_MAP = {
    'مائه':100, 'مئة':100, 'hundred':100,
    'الف':1000, 'ألف':1000, 'thousand':1000,
}
SUM_CONNECTORS = {'و', 'and'}
ALL_NUM_WORDS  = set(SINGLE_MAP) | set(TENS_MAP) | set(MULT_MAP) | SUM_CONNECTORS
WORDS_RP = r'\b(' + '|'.join(re.escape(k) for k in ALL_NUM_WORDS) + r')\b'
COMPOUND_NUM_PATTERN  = re.compile(f'{WORDS_RP}(?:\\s+{WORDS_RP})*')
DIGIT_SPACER_PATTERN  = re.compile(r'(\d)\s+(?=\d)')

def normalize_numbers(text: str) -> str:
    if not text:
        return ''
    text = text.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩',
                                         '0123456789'))
    def process_num_words(match):
        words = match.group(0).split()
        if len(words) == 1:
            w = words[0]
            for mapping in (SINGLE_MAP, TENS_MAP, MULT_MAP):
                if w in mapping:
                    return str(mapping[w])
            return w
        has_summing_clue = any(
            w in TENS_MAP or w in MULT_MAP or w in SUM_CONNECTORS for w in words
        )
        if has_summing_clue:
            total, current = 0, 0
            for w in words:
                if w in SUM_CONNECTORS: continue
                if w in SINGLE_MAP:     current += SINGLE_MAP[w]
                elif w in TENS_MAP:     current += TENS_MAP[w]
                elif w in MULT_MAP:
                    total += max(1, current) * MULT_MAP[w]
                    current = 0
            return str(total + current)
        return ''.join(str(SINGLE_MAP[w]) for w in words if w in SINGLE_MAP)
    text = COMPOUND_NUM_PATTERN.sub(process_num_words, text)
    text = DIGIT_SPACER_PATTERN.sub(r'\1', text)
    return text

def normalize_text(text: str, enable_punc: List[str] = None) -> str:
    if not text:
        return ''
    text = text.lower()
    text = unicodedata.normalize('NFC', text)
    text = URDU_CHARS_PATTERN.sub('', text)
    arabic_map = {
        'أ':'ا', 'إ':'ا', 'آ':'ا', 'ٱ':'ا', 'ٲ':'ا', 'ٳ':'ا',
        'ة':'ه',
    }
    for src, tgt in arabic_map.items():
        text = text.replace(src, tgt)
    text = normalize_numbers(text)
    text = DIACRITICS_PATTERN.sub('', text)
    if enable_punc:
        punc_to_keep = ''.join(re.escape(p) for p in enable_punc)
        dynamic_pattern = re.compile(
            rf'[^ء-يa-z0-9\s{punc_to_keep}]'
        )
        text = dynamic_pattern.sub(' ', text)
    else:
        text = CLEAN_PUNC_PATTERN.sub(' ', text)
    text = WHITESPACE_PATTERN.sub(' ', text).strip()
    return text
