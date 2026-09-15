"""The arithmetic path to a 1,000,000-row corpus under the CORPUS_REBUILD gates.

Arithmetic only: no data is read and no gate is changed. Every constant below is
quoted from its source; the two authoring rates are CLINICIAN_BRIEF's stated
ASSUMPTIONS, not measurements, and are replaced by the pilot's measured rates.

    python3 reports/measurements/corpus_1m_arithmetic.py > reports/measurements/corpus_1m_arithmetic.txt
"""

from __future__ import annotations

TARGET_ROWS = 1_000_000  # FR-04-07

# CORPUS_REBUILD §3
MAX_ROWS_PER_SEED = 50  # G1
MAX_SEED_SHARE = 0.001  # G1: no seed > 0.1% of rows
MIN_SEEDS_PER_LANGUAGE = 3_000  # G2
MIN_SEEDS_PER_CELL = 30  # G2
MAX_AUTHOR_SHARE = 0.20  # G8, per language x domain
MIN_AUTHORS_PER_LANGUAGE = 10  # CORPUS_REBUILD §2

# CLAUDE.md §9.1 language balance: each pure language 10-15%, mixed 40-60% combined.
PURE = 4
MIXED_PAIRS = 6
PURE_SHARE_EACH = 0.125  # midpoint of 10-15%
MIXED_SHARE_TOTAL = 0.50  # midpoint of 40-60%

# CLINICIAN_BRIEF: "assumptions, not measurements".
WRITE_MIN_PER_SEED = (2.0, 3.0)
VALIDATE_MIN_PER_SEED = (0.5, 0.75)  # the brief's labelling rate, used for T1 review

# Non-empty cells per language combination: domain x urgency x reporter x age group.
# Domains are BLANK (H4) and age groups BLANK (E6), so these are scenarios, not facts.
CELL_SCENARIOS = (
    ("cells <= 100 (G2's 3,000 binds)", 100),
    ("9 placeholder domains x 3 urgency x 3 reporter x 2 age groups", 9 * 3 * 3 * 2),
    ("80 domains (§9.1) x 3 urgency x 3 reporter x 1 age group", 80 * 3 * 3),
    ("80 domains x 3 urgency x 3 reporter x 2 age groups", 80 * 3 * 3 * 2),
)


def main() -> None:
    combos = PURE + MIXED_PAIRS
    rows_pure = TARGET_ROWS * PURE_SHARE_EACH
    rows_pair = TARGET_ROWS * MIXED_SHARE_TOTAL / MIXED_PAIRS
    cap = min(MAX_ROWS_PER_SEED, TARGET_ROWS * MAX_SEED_SHARE)
    print(f"Target rows (FR-04-07): {TARGET_ROWS:,}")
    print(f"Effective rows-per-seed cap (G1): min(50, 0.1% of rows) = {cap:g}")
    print(f"Rows per pure language at 12.5%: {rows_pure:,.0f}")
    print(f"Rows per mixed pair at 50% / 6:  {rows_pair:,.0f}")
    print(
        f"G1 alone: {TARGET_ROWS / cap:,.0f} distinct seeds. "
        f"G2 alone: {combos} x {MIN_SEEDS_PER_LANGUAGE:,} = {combos * MIN_SEEDS_PER_LANGUAGE:,} "
        "(if each mixed pair counts as a language)."
    )
    print()
    header = (
        f"{'Cells per combination':<64} {'seeds/comb':>10} {'seeds total':>11} "
        f"{'rows/seed pure':>14} {'rows/seed pair':>14} {'max rows at cap':>15} "
        f"{'author-hours':>15} {'h/author @40':>13} {'h/author @100':>14}"
    )
    print(header)
    for name, cells in CELL_SCENARIOS:
        per_combo = max(MIN_SEEDS_PER_LANGUAGE, MIN_SEEDS_PER_CELL * cells)
        total = combos * per_combo
        r_pure, r_pair = rows_pure / per_combo, rows_pair / per_combo
        max_rows = total * cap
        low = total * (WRITE_MIN_PER_SEED[0] + VALIDATE_MIN_PER_SEED[0]) / 60
        high = total * (WRITE_MIN_PER_SEED[1] + VALIDATE_MIN_PER_SEED[1]) / 60
        print(
            f"{name:<64} {per_combo:>10,} {total:>11,} {r_pure:>14.1f} {r_pair:>14.1f} "
            f"{max_rows:>15,.0f} {f'{low:,.0f}-{high:,.0f}':>15} "
            f"{f'{low / 40:,.0f}-{high / 40:,.0f}':>13} {f'{low / 100:,.0f}-{high / 100:,.0f}':>14}"
        )
    print()
    print(
        "If the row-level near-duplicate standard (§9.1) forces fewer frame variants per seed:"
    )
    for r in (50, 20, 10, 5, 1):
        seeds = TARGET_ROWS / r
        low = seeds * (WRITE_MIN_PER_SEED[0] + VALIDATE_MIN_PER_SEED[0]) / 60
        high = seeds * (WRITE_MIN_PER_SEED[1] + VALIDATE_MIN_PER_SEED[1]) / 60
        print(
            f"  {r:>2} rows/seed -> {seeds:>9,.0f} seeds -> {low:>7,.0f}-{high:>7,.0f} author-hours"
        )
    print()
    print("Largest defensible size for a given authoring capacity (at the G1 cap):")
    per_seed = (
        (WRITE_MIN_PER_SEED[0] + VALIDATE_MIN_PER_SEED[0]) / 60,
        (WRITE_MIN_PER_SEED[1] + VALIDATE_MIN_PER_SEED[1]) / 60,
    )
    for hours in (500, 1_000, 2_000, 4_000, 8_000):
        seeds_hi, seeds_lo = hours / per_seed[0], hours / per_seed[1]
        langs_lo = int(seeds_lo // MIN_SEEDS_PER_LANGUAGE)
        compliant = langs_lo >= combos
        print(
            f"  {hours:>5,} h -> {seeds_lo:>7,.0f}-{seeds_hi:>7,.0f} seeds -> at most "
            f"{seeds_lo * cap:>9,.0f}-{seeds_hi * cap:>9,.0f} rows; G2's 3,000-seed floor met for "
            f"{min(langs_lo, combos)} of {combos} combinations at the slower rate"
            + ("" if compliant else " -> NOT §9.1-compliant (language balance fails)")
        )
    print()
    print(
        f"Authors: >= {MIN_AUTHORS_PER_LANGUAGE} per combination (CORPUS_REBUILD §2) and "
        f"<= {MAX_AUTHOR_SHARE:.0%} each per language x domain (G8), so >= "
        f"{int(1 / MAX_AUTHOR_SHARE)} per language x domain. Across {combos} combinations that is "
        f"{MIN_AUTHORS_PER_LANGUAGE * PURE}-{MIN_AUTHORS_PER_LANGUAGE * combos} people, depending "
        "on how many bilingual authors also write in a pure language."
    )


if __name__ == "__main__":
    main()
