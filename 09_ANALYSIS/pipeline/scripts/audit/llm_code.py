#!/usr/bin/env python3
"""LLM coding harness: two independent coders apply docs/coding/codebook.md to each audit text.

Needs an Anthropic API key in the environment variable named by --api-key-env (default
ANTHROPIC_API_KEY). With no key the script stops with exit status 2 and a message; it never
produces codes without a model call. Model names are configurable (--model-a/--model-b or env
AUDIT_LLM_MODEL_A / AUDIT_LLM_MODEL_B); there are no defaults so a model is always chosen on purpose.

Each coder is a separate pass with its own calls (no shared context). The prompt contains the
codebook, language, URL and article text only. Strata, GDELT flags and weights are never sent.
Invalid or unparseable replies are stored as missing with an error note; they are not repaired.
Output per coder: data/interim/audit/llm_codes_<coder>.csv (resumable); every row carries the
SHA-256 of the codebook that was sent (freeze the codebook before the first call).

Slug basis (D16 Mode B route, --basis slug): codes an article from its URL slug alone, for articles
whose text could not be retrieved (--slug-scope missing, default) or for all articles (--slug-scope all).
Output llm_codes_slug_<coder>.csv, coding_basis = slug. These are slug-based codes, not full-text
codes, and audit_metrics.py reports them separately (never mixed into the full-text estimates).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_common import CAUSES, DIRECTION, RELEVANCE, clean_code  # noqa: E402

OUT_FIELDS = ["audit_id", "coder", "model", "coding_basis", "codebook_sha256", "relevance", "direction", "cause_primary", "cause_secondary",
              "uncertain", "rationale", "parse_error", "api_error", "text_truncated", "timestamp_utc"]

INSTRUCTIONS = """You are a careful research coder. Apply the codebook above to the article below.
Reply with ONE JSON object and nothing else, with exactly these keys:
{"relevance": "Y|N", "direction": "rising|falling|stable|mixed|none|", "cause_primary": "<code or empty>",
 "cause_secondary": "<code or empty>", "uncertain": 0|1, "rationale": "<max 30 words>"}
Leave direction, cause_primary and cause_secondary as empty strings when relevance is N.
Use only the allowed codes. If the text is empty, unreadable or not an article, reply
{"relevance": "", "direction": "", "cause_primary": "", "cause_secondary": "", "uncertain": 1, "rationale": "UNREADABLE"}.
Code only what the article says; do not use outside knowledge."""


SLUG_INSTRUCTIONS = """ONLY the URL of the article is available (no article text). Judge from the URL slug (the words in the
address) alone. If the slug is a numeric ID or carries no readable words, reply
{"relevance": "", "direction": "", "cause_primary": "", "cause_secondary": "", "uncertain": 1, "rationale": "UNINFORMATIVE_SLUG"}.
Otherwise reply with the same JSON object as for full text, and set uncertain to 1 whenever direction or cause is a guess
from a few words.
""" + INSTRUCTIONS


def build_slug_message(language: str, url: str) -> str:
    return f"Language: {language}\nURL: {url}\n\n{SLUG_INSTRUCTIONS}"


def require_key(env_name: str) -> str:
    key = os.environ.get(env_name, "").strip()
    if not key:
        print(f"ERROR: environment variable {env_name} is not set. No API key, so no LLM codes can be produced. "
              f"Nothing was written. Set the key and re-run.", file=sys.stderr)
        sys.exit(2)
    return key


def build_user_message(language: str, url: str, text: str) -> str:
    return f"Language: {language}\nURL: {url}\n\nARTICLE TEXT:\n{text}\n\n{INSTRUCTIONS}"


def parse_reply(raw: str) -> dict:
    """Validate a model reply against the codebook. Returns dict with codes (None = missing) and parse_error."""
    out = {"relevance": None, "direction": None, "cause_primary": None, "cause_secondary": None,
           "uncertain": None, "rationale": "", "parse_error": ""}
    m = re.search(r"\{.*\}", raw or "", flags=re.S)
    if not m:
        out["parse_error"] = "no_json"
        return out
    try:
        d = json.loads(m.group(0))
    except ValueError:
        out["parse_error"] = "bad_json"
        return out
    out["rationale"] = str(d.get("rationale", ""))[:300]
    rel = clean_code(d.get("relevance"), RELEVANCE)
    out["relevance"] = rel
    if rel is None:
        out["parse_error"] = "relevance_missing_or_invalid"
        return out
    dr = clean_code(d.get("direction"), DIRECTION, allow_empty=True)
    cp = clean_code(d.get("cause_primary"), CAUSES, allow_empty=True)
    cs = clean_code(d.get("cause_secondary"), CAUSES, allow_empty=True)
    errs = []
    if rel == "Y":
        if dr in (None, ""):
            errs.append("direction_missing_or_invalid")
        if cp in (None, ""):
            errs.append("cause_primary_missing_or_invalid")
        if cs is None:
            errs.append("cause_secondary_invalid")
    out["direction"], out["cause_primary"], out["cause_secondary"] = dr, cp, cs
    u = d.get("uncertain")
    out["uncertain"] = int(u) if str(u) in ("0", "1") else None
    out["parse_error"] = ";".join(errs)
    return out


def call_model(client, model: str, system: str, user: str, max_tokens: int, retries: int = 3):
    last = ""
    for attempt in range(retries):
        try:
            resp = client.messages.create(model=model, max_tokens=max_tokens, temperature=0,
                                          system=system, messages=[{"role": "user", "content": user}])
            return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text"), ""
        except Exception as e:  # network/API errors; recorded, never turned into a code
            last = f"{type(e).__name__}: {str(e)[:150]}"
            time.sleep(2 * (attempt + 1))
    return "", last


def run_coder(client, coder: str, model: str, manifest, text_dir: Path, codebook: str, out_path: Path,
              max_chars: int, max_tokens: int, limit=None, call=call_model, basis: str = "text", slug_scope: str = "missing"):
    import hashlib
    cb_hash = hashlib.sha256(codebook.encode("utf-8")).hexdigest()
    done = set()
    if out_path.exists():
        with out_path.open(encoding="utf-8") as f:
            done = {r["audit_id"] for r in csv.DictReader(f) if not r.get("api_error")}
    new = not out_path.exists()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS)
        if new:
            w.writeheader()
        for _, r in manifest.iterrows():
            aid = r["audit_id"]
            tf = text_dir / f"{aid}.txt"
            if aid in done:
                continue
            if basis == "text" and not tf.exists():
                continue
            if basis == "slug" and slug_scope == "missing" and tf.exists():
                continue
            if limit is not None and n >= limit:
                break
            if basis == "slug":
                trunc = False
                msg = build_slug_message(r["language"], r["url"])
            else:
                text = tf.read_text(encoding="utf-8", errors="replace")
                trunc = len(text) > max_chars
                msg = build_user_message(r["language"], r["url"], text[:max_chars])
            raw, err = call(client, model, codebook, msg, max_tokens)
            p = parse_reply(raw) if not err else {"relevance": None, "direction": None, "cause_primary": None,
                                                  "cause_secondary": None, "uncertain": None, "rationale": "", "parse_error": ""}
            w.writerow({"audit_id": aid, "coder": coder, "model": model, "coding_basis": basis, "codebook_sha256": cb_hash,
                        **{k: ("" if p[k] is None else p[k]) for k in ("relevance", "direction", "cause_primary", "cause_secondary", "uncertain")},
                        "rationale": p["rationale"], "parse_error": p["parse_error"], "api_error": err,
                        "text_truncated": trunc, "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
            f.flush()
            n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default="data/interim/audit/audit_manifest.csv")
    ap.add_argument("--text-dir", default="data/raw/audit_texts")
    ap.add_argument("--codebook", default="docs/coding/codebook.md")
    ap.add_argument("--out-dir", default="data/interim/audit")
    ap.add_argument("--model-a", default=os.environ.get("AUDIT_LLM_MODEL_A"))
    ap.add_argument("--model-b", default=os.environ.get("AUDIT_LLM_MODEL_B"))
    ap.add_argument("--api-key-env", default="ANTHROPIC_API_KEY")
    ap.add_argument("--max-chars", type=int, default=12000)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--basis", choices=["text", "slug"], default="text")
    ap.add_argument("--slug-scope", choices=["missing", "all"], default="missing")
    a = ap.parse_args(argv)

    key = require_key(a.api_key_env)  # stops here with a clear message when absent
    if not a.model_a or not a.model_b:
        print("ERROR: choose both models with --model-a/--model-b or AUDIT_LLM_MODEL_A/B. No default is assumed.", file=sys.stderr)
        return 2
    import anthropic
    import pandas as pd
    client = anthropic.Anthropic(api_key=key)
    manifest = pd.read_csv(a.manifest, dtype=str)
    codebook = Path(a.codebook).read_text(encoding="utf-8")
    for coder, model in (("A", a.model_a), ("B", a.model_b)):
        n = run_coder(client, coder, model, manifest, Path(a.text_dir), codebook,
                      Path(a.out_dir) / (f"llm_codes_{coder}.csv" if a.basis == "text" else f"llm_codes_slug_{coder}.csv"),
                      a.max_chars, a.max_tokens, a.limit, basis=a.basis, slug_scope=a.slug_scope)
        print(f"coder {coder} ({model}): {n} new rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
