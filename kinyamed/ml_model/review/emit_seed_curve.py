"""Emit the data behind the seeds-to-rows figure, from the gate thresholds.

WHAT THE FIGURE SHOWS. Table 2 plotted: distinct authored seed phrases on x,
the largest corpus that passes every gate on y. The curve is flat at zero until
the seed-count gate is satisfied, then rises linearly at the per-seed row cap.
The discontinuity at the seed floor is the paper's argument in one line, and our
own inventory sits on the flat part.

IT IS ARITHMETIC, NOT MEASUREMENT. Nothing here is fitted or observed. Both
numbers come from thresholds written in the corpus specification, and the
caption says so, because a curve on a page reads as data unless it is told not
to.

FAILS CLOSED, AND THE SEED COUNT IS THE POINT. `n_seeds` is read from the
generator's own inventory. If it cannot be read, this refuses and names what is
missing: a figure that silently plots a default while claiming to plot the
corpus is exactly the defect class this paper is about, and it would be worse
here than anywhere else in the repository.

Output is a plain whitespace-separated .dat that the figure reads with
pgfplots' \\addplot table. Keeping the data out of the .tex means a failed
render can be attributed to the data or the drawing, not to both at once.

Usage:
    python review/emit_seed_curve.py            # write
    python review/emit_seed_curve.py --check    # fail if stale
"""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "generated" / "seed_curve.dat"
OUT_MACROS = ROOT / "paper" / "generated" / "seed_curve_macros.tex"

X_MAX = 20_000
X_STEP = 250


class Missing(RuntimeError):
    """Something the figure depends on could not be read. Never a default."""


# The two constants the figure plots, by exact name. A name search would have
# matched MIN_SEEDS_PER_CELL (30) as readily as MIN_SEEDS_PER_LANGUAGE (3,000)
# and drawn a plausible curve with the wrong discontinuity, which is the whole
# failure this emitter exists to prevent.
SEED_FLOOR_NAME = "MIN_SEEDS_PER_LANGUAGE"
ROWS_PER_SEED_NAME = "MAX_ROWS_PER_SEED"


def gate_thresholds() -> tuple[int, int]:
    """(seed floor, rows allowed per seed), read from the gate module by name."""
    sys.path.insert(0, str(ROOT))
    try:
        gates = importlib.import_module("dataset.corpus_gates")
    except ImportError as exc:
        raise Missing(f"cannot import dataset.corpus_gates: {exc}") from exc

    values = []
    for name in (SEED_FLOOR_NAME, ROWS_PER_SEED_NAME):
        if not hasattr(gates, name):
            raise Missing(
                f"dataset/corpus_gates.py has no {name}. It was renamed or "
                "removed. The figure plots gate thresholds and must read them "
                "from the gates; it will not guess and it will not default."
            )
        value = getattr(gates, name)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise Missing(f"{name} is {value!r}, which cannot be a threshold")
        values.append(value)
    return values[0], values[1]


def n_seeds() -> int:
    """Distinct phrases the generator actually holds. No default, ever."""
    sys.path.insert(0, str(ROOT))
    try:
        vocab = importlib.import_module("dataset.vocabulary")
    except ImportError as exc:
        raise Missing(f"cannot import dataset.vocabulary: {exc}") from exc
    if not hasattr(vocab, "SYMPTOMS"):
        raise Missing("dataset/vocabulary.py has no SYMPTOMS; n_seeds is unknown")

    def walk(obj):
        if isinstance(obj, dict):
            for value in obj.values():
                yield from walk(value)
        elif isinstance(obj, (list, tuple)):
            for value in obj:
                yield from walk(value)
        else:
            yield obj

    count = len(set(walk(vocab.SYMPTOMS)))
    if not count:
        raise Missing(
            "dataset/vocabulary.py holds no phrases, so n_seeds is 0. Refusing "
            "to plot: an empty inventory and an unreadable one must not produce "
            "the same figure."
        )
    return count


def largest_passing(seeds: int, floor: int, per_seed: int) -> int:
    """Zero below the seed floor, seeds x per-seed cap above it."""
    return seeds * per_seed if seeds >= floor else 0


def render_dat() -> str:
    floor, per_seed = gate_thresholds()
    ours = n_seeds()

    xs = sorted({0, *range(0, X_MAX + 1, X_STEP), floor - 1, floor, ours, X_MAX})
    xs = [x for x in xs if 0 <= x <= X_MAX]

    lines = [
        "# GENERATED FILE - DO NOT EDIT BY HAND.",
        "# Written by review/emit_seed_curve.py.",
        "# Arithmetic on the gate thresholds in dataset/corpus_gates.py, not a",
        "# measurement: y = x * rows_per_seed where x >= seed_floor, else 0.",
        f"# seed_floor={floor}  rows_per_seed={per_seed}  ours={ours}",
        "seeds rows",
    ]
    lines += [f"{x} {largest_passing(x, floor, per_seed)}" for x in xs]
    return "\n".join(lines) + "\n"


def render_macros() -> str:
    floor, per_seed = gate_thresholds()
    ours = n_seeds()
    return (
        "% GENERATED FILE - DO NOT EDIT BY HAND.\n"
        "% Written by review/emit_seed_curve.py, so the figure's annotations\n"
        "% cannot drift from the data file beside it.\n"
        f"\\newcommand{{\\SeedFloor}}{{{floor:,}}}\n"
        f"\\newcommand{{\\SeedRowsPerSeed}}{{{per_seed:,}}}\n"
        f"\\newcommand{{\\SeedOurs}}{{{ours:,}}}\n"
        f"\\newcommand{{\\SeedOursRaw}}{{{ours}}}\n"
        f"\\newcommand{{\\SeedFloorRaw}}{{{floor}}}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        dat = render_dat()
        macros = render_macros()
    except Missing as exc:
        print(f"REFUSING TO EMIT: {exc}", file=sys.stderr)
        return 2

    if args.check:
        stale = [
            path.name
            for path, wanted in ((OUT, dat), (OUT_MACROS, macros))
            if not path.exists() or path.read_text(encoding="utf-8") != wanted
        ]
        if stale:
            print(
                f"stale: {', '.join(stale)}. Regenerate:\n"
                "  python review/emit_seed_curve.py",
                file=sys.stderr,
            )
            return 1
        print("seed_curve.dat and seed_curve_macros.tex match the gates.")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(dat, encoding="utf-8")
    OUT_MACROS.write_text(macros, encoding="utf-8")
    floor, per_seed = gate_thresholds()
    print(f"wrote {OUT.relative_to(ROOT)} and {OUT_MACROS.relative_to(ROOT)}")
    print(f"  seed floor {floor:,}   rows per seed {per_seed:,}   ours {n_seeds():,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
