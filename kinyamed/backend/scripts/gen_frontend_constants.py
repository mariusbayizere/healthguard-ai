"""Generate the frontend's urgency constants from the backend enum.

AUDIT 1.3. The clinical ordering had five independent copies. Four of them are
now one: `UrgencyLevel.priority` is the backend's definition, the ML package
reads `dataset/labels.py`, and `ml_model/tests/test_label_parity.py` fails if
those two disagree.

The fifth copy is the frontend's, and it cannot be fixed by import -- the
ordering has to cross a language boundary. The audit's conclusion was that a
cross-language constant which cannot be DRY by import must be DRY by
generation, so this script writes the TypeScript rather than a person doing it.

The ordering is NOT taken from the order the enum members happen to be
declared in. That would make a clinical sort key depend on the position of a
line in a file, which is the implicit coupling this whole exercise is about.
It is taken from `_URGENCY_PRIORITY`, which is the thing that actually sorts
the queue.

Usage:
    python scripts/gen_frontend_constants.py            # write
    python scripts/gen_frontend_constants.py --check    # fail if stale

`--check` is what `tests/unit/test_frontend_constants.py` runs, so the backend
CI job fails on a frontend constant that has drifted from the enum -- at the
point the enum changes, rather than at the point a patient is sorted wrongly.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
OUT = BACKEND.parent / "frontend" / "src" / "api" / "urgency.gen.ts"
BAND_OUT = BACKEND.parent / "frontend" / "src" / "api" / "queueBand.gen.ts"

HEADER = """\
/* GENERATED FILE — DO NOT EDIT BY HAND.
 *
 * Written by backend/scripts/gen_frontend_constants.py from
 * `app.models.triage_result.UrgencyLevel`, which is the single definition of
 * the clinical ordering. AUDIT 1.3.
 *
 * To change the ordering, change the Python enum and regenerate. Editing this
 * file makes the queue sort differently from the server that fills it, and
 * `tests/unit/test_frontend_constants.py` will fail rather than let that ship.
 */
"""


def render() -> str:
    """Return the TypeScript for the current enum."""
    # Imported inside the function so `--help` works without a database or a
    # settings object, and so the import error names this script if the
    # backend package is not installed.
    sys.path.insert(0, str(BACKEND))
    from app.models.triage_result import _URGENCY_PRIORITY, UrgencyLevel

    # Sorted by the priority VALUE, not by declaration order. If two levels
    # ever shared a priority the sort would be unstable across languages, so
    # that is an error here rather than a mystery in the queue.
    by_priority = sorted(_URGENCY_PRIORITY.items(), key=lambda kv: kv[1])
    values = [priority for _, priority in by_priority]
    if len(set(values)) != len(values):
        raise SystemExit(
            f"two urgency levels share a priority: {_URGENCY_PRIORITY}. "
            "The queue sort would be ambiguous."
        )
    missing = set(UrgencyLevel) - set(_URGENCY_PRIORITY)
    if missing:
        raise SystemExit(
            f"these levels have no priority: {sorted(m.value for m in missing)}. "
            "Every member needs one or the frontend cannot sort it."
        )

    names = [level.value for level, _ in by_priority]

    lines = [HEADER.rstrip("\n"), ""]
    lines.append("export const URGENCY = [")
    lines += [f'  "{name}",' for name in names]
    lines.append("] as const;")
    lines.append("")
    lines.append("export type Urgency = (typeof URGENCY)[number];")
    lines.append("")
    lines.append("/** Queue sort key; lower sorts earlier. Mirrors")
    lines.append(" *  `UrgencyLevel.priority` exactly, including its base. */")
    lines.append("export const URGENCY_RANK: Record<Urgency, number> = {")
    lines += [
        f"  {name}: {priority},"
        for (_, priority), name in zip(by_priority, names, strict=True)
    ]
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


BAND_HEADER = """\
/* GENERATED FILE — DO NOT EDIT BY HAND.
 *
 * Written by backend/scripts/gen_frontend_constants.py from
 * `app.models.queue_band.QueueBand`, which defines the order the queue is
 * sorted in (item 2d) and the header a clinician reads above each band.
 *
 * `tests/unit/test_frontend_constants.py` fails if this drifts from the enum.
 */
"""


def render_bands() -> str:
    """Return the TypeScript for the queue bands, in sort order, with labels."""
    sys.path.insert(0, str(BACKEND))
    from app.models.queue_band import QueueBand

    ordered = sorted(QueueBand, key=int)
    lines = [BAND_HEADER.rstrip("\n"), ""]
    lines.append("/** Queue bands, in the order the server sorts them. */")
    lines.append("export const QUEUE_BAND = [")
    lines += [f'  "{band.name}",' for band in ordered]
    lines.append("] as const;")
    lines.append("")
    lines.append("export type QueueBand = (typeof QUEUE_BAND)[number];")
    lines.append("")
    lines.append("/** The header text above each band. */")
    lines.append("export const BAND_LABEL: Record<QueueBand, string> = {")
    lines += [
        f"  {band.name}: {json.dumps(band.label, ensure_ascii=False)},"
        for band in ordered
    ]
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare against the committed file instead of writing it",
    )
    args = parser.parse_args()

    outputs = ((OUT, render()), (BAND_OUT, render_bands()))
    if args.check:
        stale = [
            out.name
            for out, rendered in outputs
            if (out.read_text(encoding="utf-8") if out.exists() else "") != rendered
        ]
        if stale:
            print(
                f"{', '.join(stale)} stale. Regenerate:\n"
                "  cd kinyamed/backend && python scripts/gen_frontend_constants.py",
                file=sys.stderr,
            )
            return 1
        print("generated frontend constants match the enums.")
        return 0

    for out, rendered in outputs:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(rendered, encoding="utf-8")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
