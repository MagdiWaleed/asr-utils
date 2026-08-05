from typing import List, Union


def _edit_distance(a: list, b: list) -> int:
    """Levenshtein distance between two sequences (substitution/insertion/
    deletion each cost 1). Equals the standard S+D+I error count used by
    WER/CER."""
    n, m = len(a), len(b)
    if n < m:
        a, b, n, m = b, a, m, n
    previous = list(range(m + 1))
    for i in range(1, n + 1):
        current = [i] + [0] * m
        ai = a[i - 1]
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                current[j] = previous[j - 1]
            else:
                current[j] = 1 + min(previous[j - 1], previous[j], current[j - 1])
        previous = current
    return previous[m]


def _as_list(x):
    return x if isinstance(x, list) else [x]


# Corpus-verified against ~150k real transcript lines (common_voice, masc,
# mgb-2, casablanca): only "لا" showed clear, unambiguous glued-repetition
# evidence (71 hits, e.g. "لالا" for spoken "لا لا" = "no no"). Every other
# short Arabic particle/interjection tested was excluded:
#   "يا"  0 glued hits in the corpus, no evidence it's even affected
#   "ها"  5 hits, but mostly laughter ("هاهاها"), too ambiguous/thin
#   "وا"  5 hits, all the same duplicated row across files, ~1 real sample
#   "ما"  302 hits, but it's all "ماما" (mom), a real lexicalized word,
#         not "ما" repeated, would corrupt every occurrence of "mom"
DEFAULT_SPLIT_REPEATED_WORDS = ["لا"]


def _split_repeated_words(text: str, words_to_split: List[str]) -> str:
    """Split a token that's an exact glued repetition of one of
    words_to_split ("لالالالا" -> "لا لا لا لا" for words_to_split=["لا"]).
    Whole-token match only, never a substring, so a real word that merely
    contains a repeated pattern internally (e.g. "مهمه", "امام") is never
    touched unless that exact word is itself in the list."""
    words_to_split = [w for w in (words_to_split or []) if w]
    if not words_to_split:
        return text
    out = []
    for tok in text.split(" "):
        for w in words_to_split:
            n = len(tok) // len(w)
            if n >= 2 and tok == w * n:
                out.extend([w] * n)
                break
        else:
            out.append(tok)
    return " ".join(out)


def _pooled_rate(reference, hypothesis, tokenize, unit_name: str, split_repeated_words) -> float:
    refs = _as_list(reference)
    hyps = _as_list(hypothesis)
    if len(refs) != len(hyps):
        raise ValueError(f"reference and hypothesis must have the same length, got {len(refs)} and {len(hyps)}")
    total_distance = 0
    total_units = 0
    for ref, hyp in zip(refs, hyps):
        if split_repeated_words:
            ref = _split_repeated_words(ref, split_repeated_words)
            hyp = _split_repeated_words(hyp, split_repeated_words)
        ref_units = tokenize(ref)
        total_distance += _edit_distance(ref_units, tokenize(hyp))
        total_units += len(ref_units)
    if total_units == 0:
        raise ValueError(f"reference must contain at least one {unit_name}")
    return total_distance / total_units


def calculate_wer(
    reference: Union[str, List[str]],
    hypothesis: Union[str, List[str]],
    split_repeated_words: List[str] = DEFAULT_SPLIT_REPEATED_WORDS,
) -> float:
    """Word Error Rate: (substitutions + deletions + insertions) / reference word count.

    reference/hypothesis: a single string pair, or equal-length lists of
    strings for batch scoring. Batch mode pools edit distance and word
    count across every pair before dividing once (a "corpus-level" WER),
    not the average of each pair's individual WER, those are different
    numbers and the pooled one is what ASR benchmarks report.

    Args:
        reference: ground-truth text, or list of ground-truth texts.
        hypothesis: predicted text, or list of predicted texts (same
            length as reference if both are lists).
        split_repeated_words: words where an exact glued repetition (e.g.
            "لالالالا" for "لا") gets split into space-separated repeats
            ("لا لا لا لا") before scoring, in both reference and
            hypothesis. Fixes word-level WER blowing up on a spacing
            convention rather than an actual content mismatch (e.g. some
            SADA transcripts glue repeated "لا"). Only a token that's
            *entirely* one of these words repeated 2+ times gets split,
            nothing else. Defaults to DEFAULT_SPLIT_REPEATED_WORDS above
            (just "لا", corpus-verified, see its comment for why every
            other candidate was excluded). Pass `[]` to disable, or your
            own list to replace it entirely (not merged with the
            default).

    Returns:
        Error rate as a fraction (0.0+, can exceed 1.0 with many
        insertions). Multiply by 100 for a percentage.
    """
    return _pooled_rate(reference, hypothesis, str.split, "word", split_repeated_words)


def calculate_cer(
    reference: Union[str, List[str]],
    hypothesis: Union[str, List[str]],
    split_repeated_words: List[str] = DEFAULT_SPLIT_REPEATED_WORDS,
) -> float:
    """Character Error Rate: (substitutions + deletions + insertions) / reference character count.

    Same batch/pooling and split_repeated_words semantics as
    calculate_wer, see its docstring. Operates on the raw character
    sequence, whitespace counts as a character like any other (so
    split_repeated_words affects this too, the inserted spaces are real
    characters).

    Args:
        reference: ground-truth text, or list of ground-truth texts.
        hypothesis: predicted text, or list of predicted texts (same
            length as reference if both are lists).
        split_repeated_words: see calculate_wer. Defaults to
            DEFAULT_SPLIT_REPEATED_WORDS.

    Returns:
        Error rate as a fraction (0.0+, can exceed 1.0 with many
        insertions). Multiply by 100 for a percentage.
    """
    return _pooled_rate(reference, hypothesis, list, "character", split_repeated_words)
