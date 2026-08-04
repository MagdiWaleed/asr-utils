# asr-normalization usage

## Function signatures

```python
def normalize_text(
    text: str,
    enable_punc: List[str] = None,
    eot_token: str = None,
    enable_special_tokens: List[str] = None,
    map_letters: Dict[str, str] = MAP_LETTERS,
) -> str: ...

def normalize_numbers(text: str) -> str: ...
```

`MAP_LETTERS` (the `map_letters` default, also importable directly):

```python
{'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ٱ': 'ا', 'ٲ': 'ا', 'ٳ': 'ا'}
```

## Basic normalization

```python
from asr_utils.normalization import normalize_text, normalize_numbers

normalize_text("Hello, World! I have twenty three books.")
# -> 'hello world i have 23 books'
```

## enable_punc — keep chosen punctuation instead of stripping it all

```python
normalize_text("Hello, World!", enable_punc=[",", "!"])
# -> 'hello, world!'
```

## eot_token — protect an end-of-turn marker through normalization

No `eot_token` given: no protection at all, `"<eot>"` is just another tag
and gets stripped like any other:

```python
normalize_text("hello <eot> world")
# -> 'hello world'
```

Only the exact token you pass is protected, whatever it looks like:

```python
normalize_text("hello <eot> world", eot_token="<eot>")
# -> 'hello <eot> world'
normalize_text("hello <turn_end> world", eot_token="<turn_end>")
# -> 'hello <turn_end> world'
```

## enable_special_tokens — keep extra tags alongside the eot marker

Every other `<...>` tag gets stripped entirely:

```python
normalize_text("<noise> hello <junk> world <eot>", eot_token="<eot>", enable_special_tokens=["<noise>"])
# -> '<noise> hello world <eot>'
```

## map_letters — override the Arabic letter-fold mapping

**Add** a mapping on top of the default:

```python
from asr_utils.normalization.normalization import MAP_LETTERS

normalize_text("مدرسة", map_letters={**MAP_LETTERS, "ة": "ه"})
# -> 'مدرسه'
```

**Remove** a mapping (drop `أ`, so it no longer folds to `ا`):

```python
removed = {k: v for k, v in MAP_LETTERS.items() if k != "أ"}
normalize_text("آمن أحمد", map_letters=removed)
# -> 'امن أحمد'   ("آ" still folds, "أ" no longer does)
```

**Remove all** folding (empty dict, not `None`, an empty override still
takes effect):

```python
normalize_text("آمن أحمد", map_letters={})
# -> 'آمن أحمد'   (nothing folded)
```

## normalize_numbers — standalone Arabic/English number-word conversion

```python
normalize_numbers("ثلاثمائة وخمسين")
# -> '350'
normalize_numbers("مائة ألف")
# -> '100000'
```

See its docstring for the known unresolved edge case (a glued
hundred-compound + tens + a trailing multiplier).
