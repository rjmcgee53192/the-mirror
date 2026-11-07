"""The Mirror dashboard — stdlib only, like The Listener.

Read-mostly public face (scores, verdicts, audit export) plus plain forms
for each role. Role checks live in core.py; the forms only carry the
actor's name so the engine can enforce who may do what.
"""
from __future__ import annotations

import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .core import Experiment, MirrorError, RESPONSE_FIELDS

DATA_DIR = os.environ.get("MIRROR_DATA", os.path.join(os.path.dirname(__file__), "..", "data"))

CSS = """
body{font-family:system-ui,sans-serif;background:#0b0e13;color:#e8ecf1;margin:0 auto;max-width:860px;padding:24px}
a{color:#8ab4ff} .card{background:#141a23;border:1px solid #263041;border-radius:12px;padding:16px;margin:14px 0}
input,textarea{width:100%;background:#0b0e13;color:#e8ecf1;border:1px solid #33415a;border-radius:8px;padding:8px;margin:4px 0}
button{background:#2f6fed;color:#fff;border:0;border-radius:8px;padding:9px 16px;cursor:pointer}
.small{color:#9aa7b8;font-size:.9em} .hit{color:#57d977} .miss{color:#ff7a7a} code{color:#ffd479}
"""


def esc(x):
    return html.escape(str(x))


def page(title, body):
    return f"<!doctype html><meta charset=utf-8><title>{esc(title)}</title><style>{CSS}</style><h1>🪞 The Mirror</h1>{body}"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body, code=200, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _form(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n).decode("utf-8") if n else ""
        return {k: v[0] for k, v in parse_qs(raw).items()}

    # ---------- GET ----------
    def do_GET(self):
        u = urlparse(self.path)
        parts = [p for p in u.path.split("/") if p]
        try:
            if u.path == "/":
                return self._home()
            if u.path == "/api/experiments":
                out = []
                for eid in Experiment.list_ids(DATA_DIR):
                    out.append(Experiment(DATA_DIR, eid).score())
                return self._send(json.dumps(out, indent=2), ctype="application/json")
            if len(parts) == 3 and parts[0] == "api" and parts[1] == "experiment":
                exp = Experiment(DATA_DIR, parts[2])
                return self._send(json.dumps(exp.public_export(), indent=2), ctype="application/json")
            if len(parts) == 2 and parts[0] == "exp":
                return self._detail(parts[1])
            self._send(page("404", "<p>Not found.</p>"), 404)
        except Exception as e:  # noqa: BLE001 — surface engine errors plainly
            self._send(page("Error", f"<div class=card>{esc(e)}</div>"), 400)

    def _home(self):
        cards = []
        for eid in Experiment.list_ids(DATA_DIR):
            s = Experiment(DATA_DIR, eid).score()
            cards.append(f"""<div class=card><b><a href="/exp/{eid}">{esc(s['title'])}</a></b>
            <div class=small>Subject: {esc(s['subject'])} · sealed {s['sealed']} · responded {s['responded']} · judged {s['judged']}</div>
            <div>Hits: <b>{s['hits']}</b> (chance expects {s['expected_by_chance']}) · p = {s['p_value']}</div>
            <div>Verdict: <b>{esc(s['verdict'])}</b></div></div>""")
        create = """<div class=card><h3>New experiment block</h3>
        <form method=post action="/create">
        <input name=title placeholder="Title" required>
        <input name=subject placeholder="Subject name (human or AI)" required>
        <input name=targeter placeholder="Targeter name (only one who knows targets)" required>
        <input name=prompter placeholder="Prompter name (sees codes only)" required>
        <input name=judge placeholder="Judge name (different from targeter)" required>
        <input name=n_trials type=number value=24 min=1>
        <button>Freeze protocol &amp; create</button></form>
        <p class=small>Subject, targeter and judge must be three different people — the engine enforces it.
        Protocol and verdict thresholds are frozen by hash at creation (PROTOCOL.md v1.0).</p></div>"""
        intro = """<p class=small>An open, blinded testing commons for extraordinary claims.
        Nobody holds two jobs: the targeter seals, the subject answers blind, the judge ranks blind.
        Every hit <i>and</i> every miss goes on the public, hash-chained ledger.</p>"""
        self._send(page("The Mirror", intro + "".join(cards) + create))

    def _detail(self, eid):
        exp = Experiment(DATA_DIR, eid)
        s = exp.score()
        p = exp.protocol
        body = f"""<p><a href="/">← all experiments</a></p>
        <div class=card><h2>{esc(p['title'])}</h2>
        <div class=small>Subject {esc(p['subject'])} · Targeter {esc(p['targeter'])} · Prompter {esc(p['prompter'])} · Judge {esc(p['judge'])}</div>
        <div class=small>Protocol hash <code>{esc(p['protocol_hash'][:16])}…</code> intact: {s['protocol_intact']} · Ledger intact: {s['ledger_intact']}</div>
        <div>Judged {s['judged']}/{p['n_trials']} · Hits <b>{s['hits']}</b> · chance expects {s['expected_by_chance']} · p = {s['p_value']}</div>
        <div>Verdict: <b>{esc(s['verdict'])}</b></div>
        <div class=small>Full audit export: <a href="/api/experiment/{eid}">/api/experiment/{eid}</a></div></div>"""
        # trial list
        rows = []
        for code, t in sorted(exp.public_export()["trials"].items()):
            mark = ""
            if t["status"] == "judged":
                mark = "<span class=hit>HIT</span>" if t["hit"] else "<span class=miss>miss</span>"
            rows.append(f"<div class=card>Code <code>{esc(code)}</code> — {esc(t['status'])} {mark}"
                        + (f"<br><span class=small>Target was: {esc(t['revealed_target']['label'])}</span>" if t["status"] == "judged" else "")
                        + "</div>")
        body += "".join(rows)
        # role forms
        body += f"""<div class=card><h3>Targeter — seal a trial</h3>
        <form method=post action="/exp/{eid}/seal">
        <input name=actor placeholder="Your name (must be the targeter)" required>
        <input name=code placeholder="6-digit code" required>
        <input name=target_label placeholder="Target label (e.g. wooden salad spoon)" required>
        <input name=target_kind placeholder="Kind: object / empty / no_box" value="object">
        <textarea name=decoys placeholder="Decoys — exactly {p['decoys_per_trial']} labels, one per line" required></textarea>
        <button>Seal (publishes hash commitment)</button></form></div>
        <div class=card><h3>Subject — lock a response</h3>
        <form method=post action="/exp/{eid}/respond">
        <input name=actor placeholder="Your name (must be the subject)" required>
        <input name=code placeholder="6-digit code" required>"""
        for f in RESPONSE_FIELDS:
            body += f"<input name={f} placeholder=\"{f.replace('_', ' ')}\" required>"
        body += f"""<input name=confidence type=number min=0 max=100 placeholder="confidence 0-100" required>
        <button>Lock response (cannot be edited)</button></form>
        <p class=small>Fragments first, name guess LAST — order is part of the protocol.</p></div>
        <div class=card><h3>Judge — rank blind</h3>
        <form method=get action="/exp/{eid}/packet">
        <input name=actor placeholder="Your name (must be the judge)" required>
        <input name=code placeholder="6-digit code" required>
        <button>Open blind packet</button></form></div>"""
        self._send(page(p["title"], body))

    # ---------- POST ----------
    def do_POST(self):
        u = urlparse(self.path)
        parts = [p for p in u.path.split("/") if p]
        f = self._form()
        try:
            if u.path == "/create":
                exp = Experiment.create(DATA_DIR, f["title"], f["subject"], f["targeter"],
                                        f["prompter"], f["judge"], int(f.get("n_trials", 24)))
                self.send_response(303); self.send_header("Location", f"/exp/{exp.exp_id}"); self.end_headers()
                return
            if len(parts) == 3 and parts[0] == "exp":
                eid, action = parts[1], parts[2]
                exp = Experiment(DATA_DIR, eid)
                if action == "packet":
                    pass
                if action == "seal":
                    decoys = [{"label": line.strip()} for line in f["decoys"].splitlines() if line.strip()]
                    exp.seal_trial(f["actor"], f["code"],
                                   {"label": f["target_label"], "kind": f.get("target_kind", "object")}, decoys)
                elif action == "respond":
                    frags = {k: f.get(k, "") for k in RESPONSE_FIELDS}
                    exp.submit_response(f["actor"], f["code"], frags, int(f["confidence"]))
                elif action == "judge":
                    ranking = [x.strip().upper() for x in f["ranking"].split(",") if x.strip()]
                    exp.submit_judgement(f["actor"], f["code"], ranking)
                else:
                    raise MirrorError("Unknown action.")
                self.send_response(303); self.send_header("Location", f"/exp/{eid}"); self.end_headers()
                return
            self._send(page("404", "<p>Not found.</p>"), 404)
        except (MirrorError, KeyError, ValueError) as e:
            self._send(page("Cannot do that", f"<div class=card><b>Blocked by the protocol engine:</b> {esc(e)}</div><p><a href='/'>← back</a></p>"), 400)


def handle_packet_get(handler, eid, qs):
    """Judge packet as its own GET (response shown beside shuffled items)."""
    q = {k: v[0] for k, v in parse_qs(qs).items()}
    exp = Experiment(DATA_DIR, eid)
    pkt = exp.judge_packet(q["actor"], q["code"])
    items = "".join(f"<div class=card><b>Item {esc(i['item_id'])}</b> — {esc(i['label'])}</div>" for i in pkt["items"])
    resp = "".join(f"<div><b>{esc(k)}</b>: {esc(v)}</div>" for k, v in pkt["response"].items())
    body = f"""<p><a href="/exp/{eid}">← experiment</a></p>
    <div class=card><h3>Subject response for code {esc(pkt['code'])}</h3>{resp}</div>
    <h3>Which item matches best? (you don't know which is the target)</h3>{items}
    <div class=card><form method=post action="/exp/{eid}/judge">
    <input type=hidden name=actor value="{esc(q['actor'])}"><input type=hidden name=code value="{esc(pkt['code'])}">
    <input name=ranking placeholder="Ranking, best first — e.g. B,A,D,C" required>
    <button>Lock ranking &amp; reveal</button></form></div>"""
    handler._send(page("Blind packet", body))


# Patch do_GET for the packet route (kept separate for readability)
_orig_get = Handler.do_GET


def _get_with_packet(self):
    u = urlparse(self.path)
    parts = [p for p in u.path.split("/") if p]
    if len(parts) == 3 and parts[0] == "exp" and parts[2] == "packet":
        try:
            return handle_packet_get(self, parts[1], u.query)
        except Exception as e:  # noqa: BLE001
            return self._send(page("Error", f"<div class=card>{esc(e)}</div>"), 400)
    return _orig_get(self)


Handler.do_GET = _get_with_packet


def main():
    port = int(os.environ.get("MIRROR_PORT", "8766"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"The Mirror dashboard: http://127.0.0.1:{port}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
