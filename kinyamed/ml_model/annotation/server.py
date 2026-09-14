"""A local web form for one annotator at a time. Standard library only.

    python -m annotation serve --db annotation.sqlite3

Binds to 127.0.0.1 and refuses any other address: this runs on the annotation
laptop and is reached from that laptop's browser only. No JavaScript, no external
assets, no cookies. Every form carries a token minted at start-up, so a page on
another site cannot post labels into it.

What an annotator sees: the item text and its language, their own progress, the
four label choices, a confidence choice, and a reason list for UNCLASSIFIABLE.
What they never see: any other annotator's label, any intended urgency, the
item's domain or presentation type (which could cue a label).

The label DEFINITIONS are not on this page. They live in the printed protocol
(`docs/protocols/d7-eval-set-annotation-protocol.md`), which cites the clinical
source; this tool contains no clinical content.
"""

from __future__ import annotations

import html
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from annotation.store import (
    CONFIDENCE_LEVELS,
    LABELS,
    UNCLASSIFIABLE_REASONS,
    AnnotationError,
    Store,
    validate_annotator,
)

LOCALHOST = "127.0.0.1"

_STYLE = """
body{font:18px/1.5 system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;color:#111}
.item{font-size:1.35rem;border:2px solid #333;border-radius:6px;padding:1rem;margin:1rem 0;white-space:pre-wrap}
fieldset{border:1px solid #999;margin:1rem 0;padding:.5rem 1rem}
label{display:block;padding:.4rem 0;min-height:44px}
button{font-size:1.1rem;min-height:44px;padding:.4rem 1.2rem}
.error{border-left:4px solid #a00;padding:.5rem 1rem;background:#fee}
.meta{color:#444}
"""


def _page(title: str, body: str) -> bytes:
    return (
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{_STYLE}</style></head>"
        f"<body><main>{body}</main></body></html>"
    ).encode()


def make_handler(store: Store, token: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            """Silent: request lines would carry annotator codes and item ids to the terminal."""

        def _send(self, status: HTTPStatus, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'",
            )
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path == "/":
                self._send(
                    HTTPStatus.OK,
                    _page(
                        "Sign in",
                        (
                            "<h1>Evaluation-set annotation</h1>"
                            "<form method='get' action='/annotate'>"
                            "<label for='a'>Your annotator code (for example A1)</label>"
                            "<input id='a' name='a' required pattern='[A-Z][0-9]{1,3}' autocomplete='off'>"
                            " <button>Start</button></form>"
                        ),
                    ),
                )
                return
            if url.path == "/annotate":
                annotator = parse_qs(url.query).get("a", [""])[0]
                self._render_item(annotator)
                return
            self._send(HTTPStatus.NOT_FOUND, _page("Not found", "<p>Not found.</p>"))

        def _render_item(self, annotator: str, error: str | None = None) -> None:
            try:
                validate_annotator(annotator)
            except AnnotationError as exc:
                self._send(
                    HTTPStatus.BAD_REQUEST,
                    _page("Bad code", f"<p class='error'>{html.escape(str(exc))}</p>"),
                )
                return
            done, total = store.progress(annotator)
            item = store.next_item(annotator)
            if item is None:
                self._send(
                    HTTPStatus.OK,
                    _page(
                        "Done",
                        f"<h1>All {total} items labelled</h1><p>Thank you. You may close this window.</p>",
                    ),
                )
                return
            labels = "".join(
                f"<label><input type='radio' name='label' value='{lab}' required> {lab}</label>"
                for lab in LABELS
            )
            confidence = "".join(
                f"<label><input type='radio' name='confidence' value='{k}' required> {k} — {v}</label>"
                for k, v in CONFIDENCE_LEVELS.items()
            )
            reasons = "".join(
                f"<label><input type='radio' name='reason' value='{r}'> {r.replace('_', ' ')}</label>"
                for r in UNCLASSIFIABLE_REASONS
            )
            body = (
                (
                    f"<p class='error' role='alert'>{html.escape(error)}</p>"
                    if error
                    else ""
                )
                + f"<p class='meta'>Annotator {html.escape(annotator)} · item {done + 1} of {total} · "
                f"language: {html.escape(item.language)}</p>"
                f"<div class='item' lang='{html.escape(item.language.split('+')[0][:2])}'>{html.escape(item.text)}</div>"
                "<form method='post' action='/annotate'>"
                f"<input type='hidden' name='token' value='{token}'>"
                f"<input type='hidden' name='a' value='{html.escape(annotator)}'>"
                f"<input type='hidden' name='item_id' value='{html.escape(item.item_id)}'>"
                f"<fieldset><legend>Urgency (definitions: printed protocol, section 3)</legend>{labels}</fieldset>"
                f"<fieldset><legend>How sure are you?</legend>{confidence}</fieldset>"
                f"<fieldset><legend>Only if UNCLASSIFIABLE: why?</legend>{reasons}</fieldset>"
                "<p>Your first answer for an item is final. Take the time you need.</p>"
                "<button>Save and next</button></form>"
            )
            self._send(HTTPStatus.OK, _page(f"Item {done + 1} of {total}", body))

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/annotate":
                self._send(
                    HTTPStatus.NOT_FOUND, _page("Not found", "<p>Not found.</p>")
                )
                return
            length = min(int(self.headers.get("Content-Length") or 0), 10_000)
            form = {
                k: v[0]
                for k, v in parse_qs(self.rfile.read(length).decode("utf-8")).items()
            }
            if not secrets.compare_digest(form.get("token", ""), token):
                self._send(
                    HTTPStatus.FORBIDDEN,
                    _page(
                        "Refused",
                        "<p class='error'>This form did not come from this session.</p>",
                    ),
                )
                return
            annotator = form.get("a", "")
            try:
                store.record(
                    annotator,
                    form.get("item_id", ""),
                    form.get("label", ""),
                    int(form.get("confidence", "0") or 0),
                    form.get("reason")
                    if form.get("label") == "UNCLASSIFIABLE"
                    else None,
                )
            except (AnnotationError, ValueError) as exc:
                self._render_item(annotator, error=str(exc))
                return
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/annotate?" + urlencode({"a": annotator}))
            self.end_headers()

    return Handler


def build_server(
    db_path: Path, host: str = LOCALHOST, port: int = 8750
) -> tuple[ThreadingHTTPServer, str]:
    if host != LOCALHOST:
        raise AnnotationError(
            f"the annotation server binds to {LOCALHOST} only, not {host!r}"
        )
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer((host, port), make_handler(Store(db_path), token))
    return server, token
