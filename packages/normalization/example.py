"""Usage examples for asr-normalization. Run directly: python example.py

See example.md for the same examples with their real output shown inline.
"""

from asr_utils.normalization import normalize_text, normalize_numbers
from asr_utils.normalization.normalization import MAP_LETTERS


def main():
    print("MAP_LETTERS:", MAP_LETTERS)

    # Basic normalization
    print(normalize_text("Hello, World! I have twenty three books."))

    # enable_punc: keep chosen punctuation instead of stripping it all
    print(normalize_text("Hello, World!", enable_punc=[",", "!"]))

    # eot_token: protect an end-of-turn marker. No eot_token given -> no
    # protection at all, "<eot>" is just another tag and gets stripped.
    print(normalize_text("hello <eot> world"))
    # Only the exact token you pass is protected, whatever it looks like.
    print(normalize_text("hello <eot> world", eot_token="<eot>"))
    print(normalize_text("hello <turn_end> world", eot_token="<turn_end>"))

    # enable_special_tokens: keep extra tags alongside the eot marker;
    # every other "<...>" tag gets stripped entirely.
    print(normalize_text(
        "<noise> hello <junk> world <eot>", eot_token="<eot>", enable_special_tokens=["<noise>"]
    ))

    # map_letters: add a mapping on top of the default
    print(normalize_text("مدرسة", map_letters={**MAP_LETTERS, "ة": "ه"}))

    # map_letters: remove one mapping (drop أ, so it no longer folds)
    removed = {k: v for k, v in MAP_LETTERS.items() if k != "أ"}
    print(normalize_text("آمن أحمد", map_letters=removed))

    # map_letters: remove all folding (empty dict, not None, still takes effect)
    print(normalize_text("آمن أحمد", map_letters={}))

    # normalize_numbers, standalone
    print(normalize_numbers("ثلاثمائة وخمسين"))
    print(normalize_numbers("مائة ألف"))
    # a whole compound before a multiplier is multiplied together
    print(normalize_numbers("خمسة وعشرين ألف"))
    # dialect spellings, a digit string before a multiplier, "ونص" after one
    print(normalize_numbers("تلات تلاف وخمستاشر"))
    print(normalize_numbers("3.5 مليون"))
    print(normalize_numbers("مليون ونص"))
    # context rules: words that aren't numbers here stay words
    print(normalize_numbers("لا أحد يعرف كل واحد"))
    print(normalize_numbers("أحد عشر"))

    # tanwin on an ordinary word folds to plain alif, decimals survive
    print(normalize_text("شكراً جداً، السعر 2.75 دولار."))


if __name__ == "__main__":
    main()
