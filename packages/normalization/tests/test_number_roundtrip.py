"""Round-trip search over spoken number forms.

Spells numbers the way people say them (MSA genitive / nominative / feminine,
spaced hundreds, tanwin, fully vowelled, Egyptian, English, inside sentences,
digits mixed with words), normalizes, and expects the digits back. Any gap in
the number maps or the parser shows up here as a concrete failing phrase.
"""
import random

from asr_utils.normalization import normalize_text

_RNG = random.Random(1)

STYLES = {
    "msa": dict(
        units=["", "واحد", "اثنين", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"],
        teens=["عشرة", "أحد عشر", "اثني عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"],
        tens=["", "", "عشرين", "ثلاثين", "أربعين", "خمسين", "ستين", "سبعين", "ثمانين", "تسعين"],
        hundreds=["", "مائة", "مائتين", "ثلاثمائة", "أربعمائة", "خمسمائة", "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"],
        short=["", "", "", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة", "عشرة"],
        scales={1000: ("ألف", "ألفين", "آلاف", "ألف"), 10**6: ("مليون", "مليونين", "ملايين", "مليون"), 10**9: ("مليار", "مليارين", "مليارات", "مليار")},
    ),
    "msa_nom": dict(
        units=["", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة"],
        teens=["عشرة", "أحد عشر", "اثنا عشر", "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", "سبعة عشر", "ثمانية عشر", "تسعة عشر"],
        tens=["", "", "عشرون", "ثلاثون", "أربعون", "خمسون", "ستون", "سبعون", "ثمانون", "تسعون"],
        hundreds=["", "مئة", "مئتان", "ثلاثمئة", "أربعمئة", "خمسمئة", "ستمئة", "سبعمئة", "ثمانمئة", "تسعمئة"],
        short=["", "", "", "ثلاثة", "أربعة", "خمسة", "ستة", "سبعة", "ثمانية", "تسعة", "عشرة"],
        scales={1000: ("ألف", "ألفان", "آلاف", "ألفاً"), 10**6: ("مليون", "مليونان", "ملايين", "مليوناً"), 10**9: ("مليار", "ملياران", "مليارات", "ملياراً")},
    ),
    "egy": dict(
        units=["", "واحد", "اتنين", "تلاتة", "اربعة", "خمسة", "ستة", "سبعة", "تمانية", "تسعة"],
        teens=["عشرة", "حداشر", "اتناشر", "تلتاشر", "اربعتاشر", "خمستاشر", "ستاشر", "سبعتاشر", "تمنتاشر", "تسعتاشر"],
        tens=["", "", "عشرين", "تلاتين", "اربعين", "خمسين", "ستين", "سبعين", "تمانين", "تسعين"],
        hundreds=["", "مية", "ميتين", "تلتمية", "ربعمية", "خمسمية", "ستمية", "سبعمية", "تمنمية", "تسعمية"],
        short=["", "", "", "تلات", "اربع", "خمس", "ست", "سبع", "تمن", "تسع", "عشر"],
        scales={1000: ("ألف", "ألفين", "تلاف", "ألف"), 10**6: ("مليون", "مليونين", "مليون", "مليون"), 10**9: ("مليار", "مليارين", "مليار", "مليار")},
    ),
}
EN_UNITS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
EN_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def below_1000(n, st):
    h, r = divmod(n, 100)
    parts = []
    if h:
        parts.append(st["hundreds"][h])
    if r:
        if r < 10:
            parts.append(st["units"][r])
        elif r < 20:
            parts.append(st["teens"][r - 10])
        else:
            t, u = divmod(r, 10)
            parts.append(f"{st['units'][u]} و{st['tens'][t]}" if u else st["tens"][t])
    return " و".join(parts)


def arabic(n, style):
    st = STYLES[style]
    if n == 0:
        return "صفر"
    groups = []
    for scale in (10**9, 10**6, 1000):
        g, n = divmod(n, scale)
        if not g:
            continue
        one, two, plural, acc = st["scales"][scale]
        if g == 1:
            groups.append(one)
        elif g == 2:
            groups.append(two)
        elif g <= 10:
            groups.append(f"{st['short'][g]} {plural}")
        else:
            groups.append(f"{below_1000(g, st)} {acc}")
    if n:
        groups.append(below_1000(n, st))
    return " و".join(groups)


def english(n):
    def b1000(n):
        h, r = divmod(n, 100)
        out = [f"{EN_UNITS[h]} hundred"] if h else []
        if r:
            if out:
                out.append("and")
            out.append(EN_UNITS[r] if r < 20 else (EN_TENS[r // 10] + (f" {EN_UNITS[r % 10]}" if r % 10 else "")))
        return " ".join(out)
    if n == 0:
        return "zero"
    out = []
    for scale, name in ((10**9, "billion"), (10**6, "million"), (1000, "thousand")):
        g, n = divmod(n, scale)
        if g:
            out.append(f"{b1000(g)} {name}")
    if n:
        out.append(b1000(n))
    return " ".join(out)


def sample(rng, k):
    nums = set(range(0, 100)) | {100, 200, 1000, 2000, 10**6, 2 * 10**6, 10**9}
    for hi in (999, 9999, 99999, 999999, 9999999, 999999999):
        nums |= {rng.randint(0, hi) for _ in range(k)}
    return sorted(nums)


FEM = dict(STYLES["msa"])
FEM.update(
    units=["", "واحدة", "اثنتين", "ثلاث", "أربع", "خمس", "ست", "سبع", "ثماني", "تسع"],
    teens=["عشر", "إحدى عشرة", "اثنتا عشرة", "ثلاث عشرة", "أربع عشرة", "خمس عشرة", "ست عشرة", "سبع عشرة", "ثماني عشرة", "تسع عشرة"],
)
SPACED = dict(STYLES["msa"])
SPACED.update(hundreds=["", "مائة", "مائتين", "ثلاث مائة", "أربع مائة", "خمس مائة", "ست مائة", "سبع مائة", "ثماني مائة", "تسع مائة"])
STYLES["fem"], STYLES["spaced"] = FEM, SPACED
ACC = dict(STYLES["msa"]); ACC["scales"] = {1000: ("ألفاً", "ألفين", "آلاف", "ألفاً"), 10**6: ("مليوناً", "مليونين", "ملايين", "مليوناً"), 10**9: ("ملياراً", "مليارين", "مليارات", "ملياراً")}
STYLES["acc"] = ACC
VOWEL = {"ثلاثة": "ثَلاثَةُ", "خمسة": "خَمْسَةِ", "عشرين": "عِشْرِينَ", "ألف": "أَلْفٍ", "مائة": "مِائَةٍ", "آلاف": "آلافٍ", "مليون": "مِلْيُونٍ", "أربعة": "أَرْبَعَةَ", "ستين": "سِتِّينَ"}

PREFIXES = ["", "دفعت ", "عندي ", "اشتريت ب ", "حوالي "]
SUFFIXES = ["", " جنيه", " ريال امبارح", " شخص", " سنة"]

def variants(n):
    out = {}
    for style in ("fem", "spaced", "acc"):
        out[style] = arabic(n, style)
    base = arabic(n, "msa")
    out["vowelled"] = " ".join(VOWEL.get(w, w) for w in base.split())
    out["waw_spaced"] = base.replace(" و", " و ")
    p, q = _RNG.choice(PREFIXES), _RNG.choice(SUFFIXES)
    spoken_n = arabic(n, _RNG.choice(["msa", "egy", "msa_nom"]))
    if spoken_n == "مية":
        # bare Egyptian "مية" is deliberately ambiguous (water / 100) unless a
        # unit or amount word is next to it; that's unit-tested separately
        spoken_n = "مائة"
    out["sentence"] = (p + spoken_n + q, p + str(n) + q)
    # mixed: digits for the thousands group, words for the rest ("25 ألف و300")
    if n >= 11000 and n < 10**6:
        th, rest = divmod(n, 1000)
        words_rest = arabic(rest, "msa") if rest else ""
        out["mixed"] = f"{th} ألف" + (f" و{words_rest}" if words_rest else "")
    return out



def _cases():
    rng = random.Random(0)
    for n in sample(rng, 150):
        for style in ("msa", "msa_nom", "egy"):
            spoken = arabic(n, style)
            # Egyptian "مية" alone is "water" as often as "hundred" and is left
            # as a word on purpose (see NEEDS_NUMBER_NEIGHBOUR).
            if not (style == "egy" and n == 100):
                yield style, spoken, str(n)
        yield "en", english(n), str(n)
        for style, v in variants(n).items():
            spoken, expected = v if isinstance(v, tuple) else (v, str(n))
            yield style, spoken, expected


def test_spoken_numbers_round_trip():
    failures = [(style, spoken, normalize_text(spoken), expected)
                for style, spoken, expected in _cases()
                if normalize_text(spoken) != expected]
    assert not failures, "\n".join(
        f"[{style}] {spoken!r} -> {got!r}, want {expected!r}" for style, spoken, got, expected in failures[:20]
    )


if __name__ == "__main__":
    test_spoken_numbers_round_trip()
