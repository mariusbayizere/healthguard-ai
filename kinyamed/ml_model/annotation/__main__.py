"""Command line for the evaluation-set annotation workflow.

    python -m annotation import-items --db ann.sqlite3 items.csv
    python -m annotation serve        --db ann.sqlite3 [--port 8750]
    python -m annotation progress     --db ann.sqlite3 A1 B1
    python -m annotation kappa        --db ann.sqlite3
    python -m annotation disagreements --db ann.sqlite3 --out disagreements.csv
    python -m annotation adjudicate   --db ann.sqlite3 ITEM_ID LABEL C1 REASON
    python -m annotation build-gold   --db ann.sqlite3 --out eval/
    python -m annotation export-labels --db ann.sqlite3 --out labels.csv

Run from kinyamed/ml_model. Everything stays in the one SQLite file and the files
you name; nothing leaves the machine.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from annotation.kappa import kappa_report, render
from annotation.store import AnnotationError, Store
from training.eval_spec import LANGUAGES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m annotation",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("import-items")
    p.add_argument("csv", type=Path)
    p = sub.add_parser("serve")
    p.add_argument("--port", type=int, default=8750)
    p = sub.add_parser("progress")
    p.add_argument("annotators", nargs="+")
    sub.add_parser("kappa")
    p = sub.add_parser("disagreements")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("adjudicate")
    p.add_argument("item_id")
    p.add_argument("label")
    p.add_argument("adjudicator")
    p.add_argument("reason")
    p = sub.add_parser("withdraw", help="coordinator: an annotator recognised an item")
    p.add_argument("item_id")
    p.add_argument("annotator")
    p.add_argument("reason")
    p = sub.add_parser(
        "request-adjudication", help="an annotator saved a label they did not intend"
    )
    p.add_argument("item_id")
    p.add_argument("annotator")
    p.add_argument("reason")
    p = sub.add_parser("build-gold")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("export-labels")
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    store = Store(args.db)
    try:
        if args.command == "import-items":
            print(f"imported {store.import_items(args.csv, LANGUAGES)} items")
        elif args.command == "serve":
            from annotation.server import build_server

            server, _ = build_server(args.db, port=args.port)
            print(f"annotation form at http://127.0.0.1:{args.port}/  (Ctrl+C to stop)")
            with contextlib.suppress(KeyboardInterrupt):
                server.serve_forever()
        elif args.command == "progress":
            for annotator in args.annotators:
                done, total = store.progress(annotator)
                print(f"{annotator}: {done} of {total}")
        elif args.command == "kappa":
            print(render(kappa_report(store.label_pairs())))
            withdrawn = store.withdrawn_items()
            if withdrawn:
                print(f"withdrawn, excluded from kappa: {len(withdrawn)} item(s)")
        elif args.command == "withdraw":
            store.withdraw(args.item_id, args.annotator, args.reason)
            print(f"{args.item_id} withdrawn")
        elif args.command == "request-adjudication":
            store.request_adjudication(args.item_id, args.annotator, args.reason)
            print(f"{args.item_id} sent to adjudication")
        elif args.command == "disagreements":
            rows = store.disagreements()
            with args.out.open("w", encoding="utf-8", newline="") as handle:
                fields = [
                    "item_id",
                    "language",
                    "text",
                    "annotator_1",
                    "label_1",
                    "annotator_2",
                    "label_2",
                    "adjudication_requested_by",
                ]
                writer = csv.DictWriter(
                    handle, [*fields, "adjudicated_label", "adjudicator_id", "reason"]
                )
                writer.writeheader()
                writer.writerows(rows)
            print(f"{len(rows)} disagreement(s) written to {args.out}")
        elif args.command == "adjudicate":
            store.adjudicate(args.item_id, args.label, args.adjudicator, args.reason)
            print(f"{args.item_id} adjudicated")
        elif args.command == "build-gold":
            manifest = store.build_gold(args.out)
            print(f"gold set written to {args.out}: {manifest['files']}")
        elif args.command == "export-labels":
            print(f"{store.export_labels(args.out)} labels written to {args.out}")
    except AnnotationError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
