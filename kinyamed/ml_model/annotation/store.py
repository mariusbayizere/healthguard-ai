"""Local storage for double, independent, blinded annotation of the evaluation set.

Standard library only (sqlite3). One file on the annotation machine; nothing is
sent anywhere. The design follows `docs/protocols/d7-eval-set-annotation-protocol.md`:

  * INDEPENDENT  an annotator's first label for an item is final and cannot be
                 overwritten; nothing in this module returns one annotator's
                 labels to another before every item carries two labels.
  * BLIND        items carry no label column at all: the author's intended
                 urgency is never imported, so it cannot be shown.
  * NO PII       annotators are opaque codes (A1, B2), never names or emails; an
                 item whose text contains a phone- or email-shaped string is
                 rejected at import, and the rejection names the item, not the text.
  * ADJUDICATED  a disagreement, or any UNCLASSIFIABLE label, is resolved by a
                 third person, recorded with a reason code; the gold set cannot be
                 built while one is unresolved. An annotator who saved the wrong
                 label on an agreed item can send it to adjudication; the first
                 label still stands for kappa.
  * TWO LABELS   an item takes exactly two independent labels; a third is refused.
  * WITHDRAWN    an item an annotator recognises (e.g. wrote) is withdrawn with a
                 reason: its labels are kept as a record, it leaves kappa and the
                 gold set, and the count is written into the gold manifest.
  * SCENARIOS    every item carries a scenario_id; the test split holds one item
                 per scenario, and no scenario is in both splits (EVAL_SET_SPEC §8).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

LABELS = ("CRITICAL", "URGENT", "ROUTINE", "UNCLASSIFIABLE")
SPLITS = ("test", "calibration")
CONFIDENCE_LEVELS = {1: "unsure", 2: "fairly sure", 3: "certain"}
UNCLASSIFIABLE_REASONS = (
    "not_a_symptom_description",
    "not_enough_information",
    "cannot_read_language",
    "other",
)
WITHDRAWAL_REASONS = ("annotator_recognised_item", "other")
ADJUDICATION_REQUEST_REASONS = ("saved_wrong_label", "other")
ADJUDICATION_REASONS = (
    "annotator_a_correct",
    "annotator_b_correct",
    "neither_correct",
    "genuinely_ambiguous_exclude",
    "unclassifiable_confirmed",
)
ANNOTATOR_ID = re.compile(r"^[A-Z][0-9]{1,3}$")
ITEM_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")

# Kept in step with backend/app/core/pii.py by a test; the two packages do not
# import each other.
_PHONE = re.compile(r"(?<![\w*+])(?<!\d\.)\+?\d(?:[ \-]?\d){8,14}(?!\w)(?!\.\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    language TEXT NOT NULL,
    scenario_id TEXT NOT NULL,
    split TEXT NOT NULL CHECK (split IN ('test', 'calibration')),
    domain TEXT,
    presentation_type TEXT
);
CREATE TABLE IF NOT EXISTS annotations (
    item_id TEXT NOT NULL REFERENCES items (item_id),
    annotator_id TEXT NOT NULL,
    label TEXT NOT NULL CHECK (label IN ('CRITICAL', 'URGENT', 'ROUTINE', 'UNCLASSIFIABLE')),
    confidence INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 3),
    unclassifiable_reason TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (item_id, annotator_id)
);
CREATE TABLE IF NOT EXISTS withdrawals (
    item_id TEXT PRIMARY KEY REFERENCES items (item_id),
    annotator_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS adjudication_requests (
    item_id TEXT NOT NULL REFERENCES items (item_id),
    annotator_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (item_id, annotator_id)
);
CREATE TABLE IF NOT EXISTS adjudications (
    item_id TEXT PRIMARY KEY REFERENCES items (item_id),
    label TEXT NOT NULL CHECK (label IN ('CRITICAL', 'URGENT', 'ROUTINE', 'UNCLASSIFIABLE')),
    adjudicator_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class AnnotationError(ValueError):
    """The operation would break independence, blinding, PII or completeness rules."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def contains_pii(text: str) -> bool:
    return bool(_PHONE.search(text) or _EMAIL.search(text))


def validate_annotator(annotator_id: str) -> str:
    if not ANNOTATOR_ID.match(annotator_id or ""):
        raise AnnotationError(
            "annotator IDs are opaque codes such as A1 or B2 (a capital letter and up "
            "to three digits); names and email addresses are not stored"
        )
    return annotator_id


@dataclass(frozen=True)
class Item:
    item_id: str
    text: str
    language: str
    scenario_id: str
    split: str


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.executescript(_SCHEMA)
        self.db.execute("PRAGMA foreign_keys = ON")

    # ── Items ────────────────────────────────────────────────────────────────
    def import_items(self, csv_path: Path, languages: Iterable[str]) -> int:
        allowed = set(languages)
        with csv_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        required = {"item_id", "text", "language", "split"}
        if not rows or not required <= rows[0].keys():
            raise AnnotationError(f"items CSV needs columns {sorted(required)}")
        if "label" in rows[0] or "gold_label" in rows[0] or "urgency" in rows[0]:
            raise AnnotationError(
                "items CSV carries a label column; remove it — annotators must not be "
                "able to see an intended urgency"
            )
        problems: list[str] = []
        for row in rows:
            item_id = row["item_id"].strip()
            if not ITEM_ID.match(item_id):
                problems.append(f"{item_id!r}: bad item_id")
            if row["language"].strip() not in allowed:
                problems.append(
                    f"{item_id}: language {row['language']!r} not in the spec"
                )
            if row["split"].strip() not in SPLITS:
                problems.append(f"{item_id}: split must be one of {SPLITS}")
            if not (row.get("scenario_id") or "").strip():
                problems.append(f"{item_id}: no scenario_id (every item carries one)")
            if not row["text"].strip():
                problems.append(f"{item_id}: empty text")
            elif contains_pii(row["text"]):
                problems.append(
                    f"{item_id}: text contains a phone- or email-shaped string"
                )
        problems += self._scenario_and_id_problems(rows)
        if problems:
            raise AnnotationError(
                "import refused, nothing written:\n  " + "\n  ".join(problems)
            )
        with self.db:
            for row in rows:
                self.db.execute(
                    "INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        row["item_id"].strip(),
                        row["text"].strip(),
                        row["language"].strip(),
                        row["scenario_id"].strip(),
                        row["split"].strip(),
                        (row.get("domain") or "").strip() or None,
                        (row.get("presentation_type") or "").strip() or None,
                    ),
                )
        return len(rows)

    def _scenario_and_id_problems(self, rows: list[dict[str, str]]) -> list[str]:
        """Duplicate ids, and the scenario rules of EVAL_SET_SPEC §8, across the file
        and everything already imported."""
        problems: list[str] = []
        existing_ids = {r[0] for r in self.db.execute("SELECT item_id FROM items")}
        splits: dict[str, set[str]] = {}
        test_items: dict[str, list[str]] = {}
        for scenario, split, item in self.db.execute(
            "SELECT scenario_id, split, item_id FROM items"
        ):
            splits.setdefault(scenario, set()).add(split)
            if split == "test":
                test_items.setdefault(scenario, []).append(item)
        seen: set[str] = set()
        for row in rows:
            item_id = row["item_id"].strip()
            if item_id in existing_ids:
                problems.append(f"{item_id}: already imported")
            if item_id in seen:
                problems.append(f"{item_id}: appears twice in this file")
            seen.add(item_id)
            scenario = (row.get("scenario_id") or "").strip()
            if not scenario:
                continue
            split = row["split"].strip()
            splits.setdefault(scenario, set()).add(split)
            if split == "test":
                test_items.setdefault(scenario, []).append(item_id)
        for scenario, items in sorted(test_items.items()):
            if len(items) > 1:
                problems.append(
                    f"scenario {scenario}: {len(items)} test items ({', '.join(items)}); "
                    "one test item per scenario, paraphrases go to calibration"
                )
        for scenario, used in sorted(splits.items()):
            if {"test", "calibration"} <= used:
                problems.append(
                    f"scenario {scenario}: in both the test and calibration splits"
                )
        return problems

    def item_count(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM items").fetchone()[0])

    # ── Annotation ───────────────────────────────────────────────────────────
    @staticmethod
    def _order_key(annotator_id: str, item_id: str) -> str:
        """A stable, per-annotator shuffle: order effects do not align across annotators."""
        return hashlib.sha256(f"{annotator_id}:{item_id}".encode()).hexdigest()

    def next_item(self, annotator_id: str) -> Item | None:
        validate_annotator(annotator_id)
        rows = self.db.execute(
            "SELECT item_id, text, language, scenario_id, split FROM items WHERE item_id NOT IN "
            "(SELECT item_id FROM annotations WHERE annotator_id = ?) "
            "AND item_id NOT IN (SELECT item_id FROM withdrawals) "
            "AND item_id NOT IN (SELECT item_id FROM annotations GROUP BY item_id "
            "HAVING COUNT(*) >= 2)",
            (annotator_id,),
        ).fetchall()
        if not rows:
            return None
        row = min(rows, key=lambda r: self._order_key(annotator_id, r[0]))
        return Item(*row)

    def record(
        self,
        annotator_id: str,
        item_id: str,
        label: str,
        confidence: int,
        unclassifiable_reason: str | None = None,
    ) -> None:
        validate_annotator(annotator_id)
        if label not in LABELS:
            raise AnnotationError(f"label must be one of {LABELS}")
        if confidence not in CONFIDENCE_LEVELS:
            raise AnnotationError(
                "confidence must be 1 (unsure), 2 (fairly sure) or 3 (certain)"
            )
        if label == "UNCLASSIFIABLE":
            if unclassifiable_reason not in UNCLASSIFIABLE_REASONS:
                raise AnnotationError(
                    f"UNCLASSIFIABLE needs a reason from {UNCLASSIFIABLE_REASONS}"
                )
        elif unclassifiable_reason is not None:
            raise AnnotationError("a reason is recorded only for UNCLASSIFIABLE")
        if (
            self.db.execute(
                "SELECT 1 FROM items WHERE item_id = ?", (item_id,)
            ).fetchone()
            is None
        ):
            raise AnnotationError(f"unknown item {item_id!r}")
        if self._withdrawn(item_id):
            raise AnnotationError(f"{item_id} is withdrawn and takes no further labels")
        others = self.db.execute(
            "SELECT COUNT(*) FROM annotations WHERE item_id = ? AND annotator_id != ?",
            (item_id, annotator_id),
        ).fetchone()[0]
        if others >= 2:
            raise AnnotationError(
                f"{item_id} already has two independent labels; a third is not recorded"
            )
        try:
            with self.db:
                self.db.execute(
                    "INSERT INTO annotations VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        item_id,
                        annotator_id,
                        label,
                        confidence,
                        unclassifiable_reason,
                        _now(),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise AnnotationError(
                f"{annotator_id} has already labelled {item_id}; a first independent "
                "label is final (see the protocol for recording a mistake)"
            ) from error

    def progress(self, annotator_id: str) -> tuple[int, int]:
        validate_annotator(annotator_id)
        done = self.db.execute(
            "SELECT COUNT(*) FROM annotations WHERE annotator_id = ?", (annotator_id,)
        ).fetchone()[0]
        return int(done), self.item_count()

    def _withdrawn(self, item_id: str) -> bool:
        return (
            self.db.execute(
                "SELECT 1 FROM withdrawals WHERE item_id = ?", (item_id,)
            ).fetchone()
            is not None
        )

    def _require_item(self, item_id: str) -> None:
        if (
            self.db.execute(
                "SELECT 1 FROM items WHERE item_id = ?", (item_id,)
            ).fetchone()
            is None
        ):
            raise AnnotationError(f"unknown item {item_id!r}")

    def withdraw(self, item_id: str, annotator_id: str, reason: str) -> None:
        """Coordinator: an annotator recognised this item (D7 protocol §4)."""
        validate_annotator(annotator_id)
        if reason not in WITHDRAWAL_REASONS:
            raise AnnotationError(f"reason must be one of {WITHDRAWAL_REASONS}")
        self._require_item(item_id)
        try:
            with self.db:
                self.db.execute(
                    "INSERT INTO withdrawals VALUES (?, ?, ?, ?)",
                    (item_id, annotator_id, reason, _now()),
                )
        except sqlite3.IntegrityError as error:
            raise AnnotationError(f"{item_id} is already withdrawn") from error

    def withdrawn_items(self) -> list[str]:
        return [
            r[0]
            for r in self.db.execute("SELECT item_id FROM withdrawals ORDER BY item_id")
        ]

    def request_adjudication(
        self, item_id: str, annotator_id: str, reason: str
    ) -> None:
        """An annotator saved a label they did not intend (D7 protocol §4). The first
        label stands for kappa; the item must be adjudicated before the gold set."""
        validate_annotator(annotator_id)
        if reason not in ADJUDICATION_REQUEST_REASONS:
            raise AnnotationError(
                f"reason must be one of {ADJUDICATION_REQUEST_REASONS}"
            )
        self._require_item(item_id)
        labelled = self.db.execute(
            "SELECT 1 FROM annotations WHERE item_id = ? AND annotator_id = ?",
            (item_id, annotator_id),
        ).fetchone()
        if labelled is None:
            raise AnnotationError(
                f"{annotator_id} has not labelled {item_id}; only its annotators can "
                "send it to adjudication"
            )
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO adjudication_requests VALUES (?, ?, ?, ?)",
                (item_id, annotator_id, reason, _now()),
            )

    def _requested_by(self, item_id: str) -> str | None:
        row = self.db.execute(
            "SELECT group_concat(annotator_id, ' ') FROM adjudication_requests "
            "WHERE item_id = ?",
            (item_id,),
        ).fetchone()
        return row[0] if row and row[0] else None

    # ── Only once every item has two independent labels ──────────────────────
    def _pairs(self) -> list[tuple[str, str, str, str, str, str]]:
        """(item_id, language, annotator 1, label 1, annotator 2, label 2), refusing if incomplete."""
        counts = self.db.execute(
            "SELECT i.item_id, COUNT(a.annotator_id) FROM items i "
            "LEFT JOIN annotations a USING (item_id) "
            "WHERE i.item_id NOT IN (SELECT item_id FROM withdrawals) GROUP BY i.item_id"
        ).fetchall()
        incomplete = [item for item, n in counts if n != 2]
        if incomplete:
            raise AnnotationError(
                f"{len(incomplete)} item(s) do not have exactly two labels; agreement and "
                "disagreements are not shown before annotation is complete, so neither "
                "annotator can be influenced"
            )
        rows = self.db.execute(
            "SELECT i.item_id, i.language, a.annotator_id, a.label FROM items i "
            "JOIN annotations a USING (item_id) "
            "WHERE i.item_id NOT IN (SELECT item_id FROM withdrawals) "
            "ORDER BY i.item_id, a.annotator_id"
        ).fetchall()
        pairs = []
        for k in range(0, len(rows), 2):
            (item, lang, a1, l1), (_, _, a2, l2) = rows[k], rows[k + 1]
            pairs.append((item, lang, a1, l1, a2, l2))
        return pairs

    def label_pairs(self) -> list[tuple[str, str, str]]:
        """(language, label 1, label 2) for kappa. Refuses before completion."""
        return [(lang, l1, l2) for _, lang, _, l1, _, l2 in self._pairs()]

    def disagreements(self) -> list[dict[str, str]]:
        out = []
        for item, lang, a1, l1, a2, l2 in self._pairs():
            requested = self._requested_by(item)
            if (
                l1 != l2 or "UNCLASSIFIABLE" in (l1, l2) or requested
            ) and not self._adjudicated(item):
                text = self.db.execute(
                    "SELECT text FROM items WHERE item_id = ?", (item,)
                ).fetchone()[0]
                out.append(
                    {
                        "item_id": item,
                        "language": lang,
                        "text": text,
                        "annotator_1": a1,
                        "label_1": l1,
                        "annotator_2": a2,
                        "label_2": l2,
                        "adjudication_requested_by": requested or "",
                    }
                )
        return out

    def _adjudicated(self, item_id: str) -> bool:
        return (
            self.db.execute(
                "SELECT 1 FROM adjudications WHERE item_id = ?", (item_id,)
            ).fetchone()
            is not None
        )

    def adjudicate(
        self, item_id: str, label: str, adjudicator_id: str, reason: str
    ) -> None:
        validate_annotator(adjudicator_id)
        if label not in LABELS:
            raise AnnotationError(f"label must be one of {LABELS}")
        if reason not in ADJUDICATION_REASONS:
            raise AnnotationError(f"reason must be one of {ADJUDICATION_REASONS}")
        pair = next((p for p in self._pairs() if p[0] == item_id), None)
        if pair is None:
            raise AnnotationError(f"unknown item {item_id!r}")
        if adjudicator_id in (pair[2], pair[4]):
            raise AnnotationError(
                "an item is adjudicated by a third person, not one of its annotators"
            )
        if (
            pair[3] == pair[5]
            and "UNCLASSIFIABLE" not in (pair[3], pair[5])
            and not self._requested_by(item_id)
        ):
            raise AnnotationError(
                f"{item_id} is not in disagreement and no annotator sent it to adjudication"
            )
        with self.db:
            self.db.execute(
                "INSERT INTO adjudications VALUES (?, ?, ?, ?, ?)",
                (item_id, label, adjudicator_id, reason, _now()),
            )

    def build_gold(self, out_dir: Path) -> dict:
        """Write gold_<split>.csv and a manifest with SHA-256 digests. Refuses if unresolved."""
        unresolved = self.disagreements()
        if unresolved:
            raise AnnotationError(
                f"{len(unresolved)} disagreement(s) are not adjudicated"
            )
        out_dir.mkdir(parents=True, exist_ok=True)
        withdrawn = self.withdrawn_items()
        manifest: dict = {
            "built_at": _now(),
            "files": {},
            "counts": {},
            "withdrawn": {"count": len(withdrawn), "items": withdrawn},
        }
        adjudicated = dict(
            self.db.execute("SELECT item_id, label FROM adjudications").fetchall()
        )
        for split in SPLITS:
            path = out_dir / f"gold_{split}.csv"
            counts: dict[str, dict[str, int]] = {}
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "item_id",
                        "text",
                        "language",
                        "gold_label",
                        "scenario_id",
                        "split",
                    ]
                )
                for item, lang, _, l1, _, l2 in self._pairs():
                    row = self.db.execute(
                        "SELECT text, scenario_id, split FROM items WHERE item_id = ?",
                        (item,),
                    ).fetchone()
                    if row[2] != split:
                        continue
                    gold = adjudicated.get(item, l1 if l1 == l2 else None)
                    writer.writerow([item, row[0], lang, gold, row[1], split])
                    counts.setdefault(lang, {}).setdefault(gold, 0)
                    counts[lang][gold] += 1
            manifest["files"][split] = {
                "path": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            manifest["counts"][split] = counts
        (out_dir / "gold_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True)
        )
        return manifest

    def export_labels(self, path: Path) -> int:
        self._pairs()  # refuses before completion
        rows = self.db.execute(
            "SELECT a.item_id, i.language, a.annotator_id, a.label, a.confidence, "
            "a.unclassifiable_reason, a.created_at, "
            "CASE WHEN w.item_id IS NULL THEN 'no' ELSE 'yes' END "
            "FROM annotations a JOIN items i USING (item_id) "
            "LEFT JOIN withdrawals w ON w.item_id = a.item_id "
            "ORDER BY a.item_id, a.annotator_id"
        ).fetchall()
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "item_id",
                    "language",
                    "annotator_id",
                    "label",
                    "confidence",
                    "unclassifiable_reason",
                    "created_at",
                    "withdrawn",
                ]
            )
            writer.writerows(rows)
        return len(rows)
