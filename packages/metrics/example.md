# asr-metrics usage

## Function signatures

```python
def calculate_wer(
    reference: Union[str, List[str]],
    hypothesis: Union[str, List[str]],
    split_repeated_words: List[str] = DEFAULT_SPLIT_REPEATED_WORDS,
) -> float: ...

def calculate_cer(
    reference: Union[str, List[str]],
    hypothesis: Union[str, List[str]],
    split_repeated_words: List[str] = DEFAULT_SPLIT_REPEATED_WORDS,
) -> float: ...
```

`DEFAULT_SPLIT_REPEATED_WORDS` (also importable directly):

```python
['لا']
```

Both return a fraction (`0.0+`, can exceed `1.0` with many insertions).
Multiply by 100 for a percentage. `reference`/`hypothesis` can each be a
single string, or equal-length lists of strings for batch scoring.

## Single pair

```python
from asr_utils.metrics import calculate_wer, calculate_cer

calculate_wer("the cat sat on the mat", "the cat stood on the mat")
# -> 0.16666666666666666
calculate_cer("cat", "cut")
# -> 0.3333333333333333
```

## Batch — pooled, not averaged

Batch mode sums edit distance and unit count across every pair before
dividing once. This is a different (and correct, for benchmark purposes)
number than averaging each pair's individual WER:

```python
refs = ["a b", "a b c d"]
hyps = ["a x", "a b c x"]
calculate_wer(refs, hyps)
# -> 0.3333333333333333   # pooled: (1+1) / (2+4)
```

Averaging instead would give `(0.5 + 0.25) / 2 = 0.375`, a different
(wrong, for a corpus-level metric) number.

## As a percentage

```python
calculate_wer("the cat sat", "the dog sat") * 100
# -> 33.33333333333333
```

## split_repeated_words — fix a glued-repetition spacing artifact

Some transcripts (e.g. SADA) glue a repeated word into one token
(`"لالالالا"`) while a hypothesis writes it spaced (`"لا لا لا لا"`).
Same content, but word-level WER used to score it as 4 errors (400%).
`DEFAULT_SPLIT_REPEATED_WORDS` (just `"لا"`) is on by default, no param
needed:

```python
calculate_wer("لالالالا", "لا لا لا لا")
# -> 0.0
```

`"لا"` is the only word that survived corpus verification (~150k real
transcript lines): `"يا"` had zero glued evidence, `"ها"` was mostly
laughter (`"هاهاها"`), `"وا"` had one real sample, and `"ما"` was
disqualified outright, it's almost always `"ماما"` (mom), a real
lexicalized word, not `"ما"` repeated. A blanket auto-detector (any
repeated-substring shape) would wrongly mangle real words too, e.g.
`"مهمه"`, `"امام"` — that's exactly why this only ever touches a token
that's *entirely* a listed word repeated 2+ times, nothing else, and
why the default list is deliberately this small:

```python
calculate_wer("مهمه شي", "مهمه شي")
# -> 0.0   ("مهمه" isn't in the default list, untouched either way)
```

Disable entirely, or override with your own list (replaces the default,
doesn't merge with it):

```python
calculate_wer("لالالالا", "لا لا لا لا", split_repeated_words=[])
# -> 4.0
```

## Validated against real data

Cross-checked against `a separate project`/`an evaluation corpus`'s published
`results.json` numbers by normalizing (`asr_utils.normalization`,
default settings) and pooling every reference/hypothesis pair per
dataset:

| dataset | samples | my WER | published WER | diff |
|---|---|---|---|---|
| common_voice | 10,508 | 11.518 | 11.330 | +0.19 |
| mgb-2 | 5,365 | 13.389 | 13.291 | +0.10 |
| casablanca | 6,818 | 60.312 | 59.653 | +0.66 |

Agreement within ~1 point on 3 of 4 datasets checked (the 4th, masc,
diverged by ~9 points; investigated and ruled out an implementation bug —
verified via hand-worked cases, the standard Levenshtein DP, and a
difflib cross-check on 2000 real samples — the cause is external to this
package, likely a stale `results.json` or a different reference source
upstream).
