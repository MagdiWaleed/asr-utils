from asr_utils.metrics import calculate_wer, calculate_cer


def _raises(fn, *args):
    try:
        fn(*args)
    except ValueError:
        return True
    return False


def test_wer_identical():
    assert calculate_wer("the cat sat", "the cat sat") == 0.0


def test_wer_known_case():
    # ref "the cat sat on the mat" (6 words), hyp swaps "sat"->"stood" (1 sub)
    assert calculate_wer("the cat sat on the mat", "the cat stood on the mat") == 1 / 6


def test_wer_insertion_and_deletion():
    # ref "a b c" (3 words), hyp "a b c d" -> 1 insertion
    assert calculate_wer("a b c", "a b c d") == 1 / 3
    # ref "a b c" (3 words), hyp "a b" -> 1 deletion
    assert calculate_wer("a b c", "a b") == 1 / 3


def test_wer_empty_hypothesis():
    assert calculate_wer("a b c", "") == 1.0  # 3 deletions / 3 words


def test_wer_empty_reference_raises():
    assert _raises(calculate_wer, "", "a b c")


def test_wer_batch_is_pooled_not_averaged():
    # pair 1: 1 error / 2 words, pair 2: 1 error / 4 words
    # averaged would be (0.5 + 0.25) / 2 = 0.375
    # pooled (correct) is (1 + 1) / (2 + 4) = 0.333...
    refs = ["a b", "a b c d"]
    hyps = ["a x", "a b c x"]
    assert abs(calculate_wer(refs, hyps) - 2 / 6) < 1e-9


def test_wer_batch_length_mismatch_raises():
    assert _raises(calculate_wer, ["a b"], ["a b", "c d"])


def test_cer_identical():
    assert calculate_cer("hello", "hello") == 0.0


def test_cer_known_case():
    # "cat" -> "cut": 1 substitution / 3 chars
    assert calculate_cer("cat", "cut") == 1 / 3


def test_cer_counts_whitespace():
    # "a b" (3 chars incl space) -> "ab" (missing space, 1 deletion)
    assert calculate_cer("a b", "ab") == 1 / 3


def test_cer_batch_is_pooled():
    refs = ["ab", "abcd"]
    hyps = ["ax", "abcx"]
    assert abs(calculate_cer(refs, hyps) - 2 / 6) < 1e-9


def test_cer_empty_reference_raises():
    assert _raises(calculate_cer, "", "abc")


def test_split_repeated_words_fixes_glued_repetition_by_default():
    # the actual reported case: glued repetition inflates word-level WER
    # for content that's actually identical. "لا" is on by default
    # (DEFAULT_SPLIT_REPEATED_WORDS), corpus-verified, no param needed.
    assert calculate_wer("لالالالا", "لا لا لا لا") == 0.0
    assert calculate_wer("لالالالا", "لا لا لا لا", split_repeated_words=[]) == 4.0  # disabled

    # affects CER too (the fix removes the spurious inserted-space diff)
    assert calculate_cer("لالالالا", "لا لا لا لا") == 0.0
    assert calculate_cer("لالالالا", "لا لا لا لا", split_repeated_words=[]) == 3 / 8  # disabled


def test_split_repeated_words_override_replaces_default():
    # passing a list replaces the default entirely, doesn't merge with it
    assert calculate_wer("لالالالا", "لا لا لا لا", split_repeated_words=["يا"]) == 4.0


def test_split_repeated_words_only_touches_whitelisted_word():
    # a real word with the same repeated-pair shape is untouched unless
    # it's explicitly in the list
    assert calculate_wer("مهمه شي", "مهمه شي", split_repeated_words=["لا"]) == 0.0


def test_split_repeated_words_batch_mode():
    refs = ["لالالالا", "hello"]
    hyps = ["لا لا لا لا", "hello"]
    assert calculate_wer(refs, hyps, split_repeated_words=["لا"]) == 0.0


if __name__ == "__main__":
    test_wer_identical()
    test_wer_known_case()
    test_wer_insertion_and_deletion()
    test_wer_empty_hypothesis()
    test_wer_empty_reference_raises()
    test_wer_batch_is_pooled_not_averaged()
    test_wer_batch_length_mismatch_raises()
    test_cer_identical()
    test_cer_known_case()
    test_cer_counts_whitespace()
    test_cer_batch_is_pooled()
    test_cer_empty_reference_raises()
    test_split_repeated_words_fixes_glued_repetition_by_default()
    test_split_repeated_words_override_replaces_default()
    test_split_repeated_words_only_touches_whitelisted_word()
    test_split_repeated_words_batch_mode()
    print("ok")
