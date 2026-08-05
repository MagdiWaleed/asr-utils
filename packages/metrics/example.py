"""Usage examples for asr-metrics. Run directly: python example.py

See example.md for the same examples with their real output shown inline.
"""

from asr_utils.metrics import calculate_wer, calculate_cer, DEFAULT_SPLIT_REPEATED_WORDS


def main():
    # Single pair
    print(calculate_wer("the cat sat on the mat", "the cat stood on the mat"))
    print(calculate_cer("cat", "cut"))

    # Batch (pooled): sums edit distance and unit count across every pair
    # before dividing once, this is the correct way to aggregate over a
    # dataset. Averaging each pair's individual WER instead gives a
    # different (wrong, for benchmark purposes) number.
    refs = ["a b", "a b c d"]
    hyps = ["a x", "a b c x"]
    print(calculate_wer(refs, hyps))

    # Multiply by 100 for a percentage, matching how ASR benchmarks report it
    print(calculate_wer("the cat sat", "the dog sat") * 100)

    # split_repeated_words: fix a glued-repetition spacing convention
    # (e.g. some SADA transcripts write "لالالالا" instead of
    # "لا لا لا لا") from blowing up WER/CER on identical content.
    # DEFAULT_SPLIT_REPEATED_WORDS (just "لا", corpus-verified) is on by
    # default, no param needed:
    print(DEFAULT_SPLIT_REPEATED_WORDS)
    print(calculate_wer("لالالالا", "لا لا لا لا"))
    # disable entirely, or override with your own list (replaces the
    # default, doesn't merge with it)
    print(calculate_wer("لالالالا", "لا لا لا لا", split_repeated_words=[]))
    print(calculate_wer("مهمه شي", "مهمه شي"))  # untouched, "مهمه" isn't in the default list


if __name__ == "__main__":
    main()
