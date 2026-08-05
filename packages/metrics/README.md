# asr-metrics

WER/CER for ASR evaluation. Replaces `jiwer`. Standard Levenshtein
distance, pure stdlib, no dependencies.

```python
from asr_utils.metrics import calculate_wer, calculate_cer

calculate_wer(reference, hypothesis)
calculate_cer(reference, hypothesis)
```

`reference`/`hypothesis` are each a single string, or equal-length lists
of strings for batch (pooled) scoring.

## Equations

$$
\text{WER} = \frac{\sum_{i=1}^{N} \text{EditDistance}(\text{ref}_i^{words},\ \text{hyp}_i^{words})}{\sum_{i=1}^{N} |\text{ref}_i^{words}|}
$$

$$
\text{CER} = \frac{\sum_{i=1}^{N} \text{EditDistance}(\text{ref}_i^{chars},\ \text{hyp}_i^{chars})}{\sum_{i=1}^{N} |\text{ref}_i^{chars}|}
$$

`EditDistance` is standard Levenshtein distance (substitutions +
insertions + deletions, each cost 1). `N` is the batch size (`N=1` for
a single string pair). Both sums are **pooled across the whole batch
before dividing once**, not the mean of each pair's individual rate,
that's a different (wrong, for corpus-level reporting) number.

Equivalently for `N=1`, the familiar single-utterance form:

$$
\text{WER} = \frac{S + D + I}{N_{\text{ref words}}}, \qquad
\text{CER} = \frac{S + D + I}{N_{\text{ref chars}}}
$$

where `S`/`D`/`I` are substitutions/deletions/insertions from the
optimal alignment.

## split_repeated_words

Both functions take an opt-in `split_repeated_words` param, defaulting
to `DEFAULT_SPLIT_REPEATED_WORDS` (`["لا"]`, corpus-verified). It fixes
word-level WER/CER blowing up on a glued-repetition spacing artifact
(some transcripts write `"لالالالا"` where a hypothesis says
`"لا لا لا لا"`, same content, previously scored as 4 errors). See
[`example.md`](example.md) for the full add/disable/override examples
and the per-candidate corpus-verification reasoning.

## Usage examples

See [`example.md`](example.md) (with real output shown inline) or run
[`example.py`](example.py) directly.

## Validated against real data

Reproduces published `results.json` WER/CER within ~1 point on 3 of 4
real benchmark datasets after normalizing with `asr_utils.normalization`.
See `example.md` for the full table and the one dataset that diverged
(ruled out as an implementation bug, cause external to this package).
