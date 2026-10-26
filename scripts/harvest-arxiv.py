#!/usr/bin/env python3
"""harvest-arxiv -- a reproducible research harvest against the arXiv API.

WHY (2026-10-26). The founder asked for deep research on the estate's working
process and on "anything an agent does that can be done by a machine or a decision
model". A research claim without a source is not a finding, so the harvest is
committed next to the digest it feeds: the raw records, every field, so any
citation in the digest can be checked against the file that produced it.

THE INSTRUMENT. Standard library only (urllib + xml.etree), so it runs on a
laptop with no install step and inside CI without a wheel. The arXiv API is the
one corpus endpoint that needs no key and returns stable identifiers.

    scripts/harvest-arxiv.py --out docs/research/2026-10-26-machine-first-harvest.json
    scripts/harvest-arxiv.py --verify docs/research/2026-10-26-machine-first-harvest.json

`--verify` is the falsifier: it re-reads the harvest and refuses when a record
cited by the digest is not in the file.

NO INVENTED FIELDS. Every record carries what the API returned: id, title,
summary, authors, published, updated, categories, primary category, doi, and the
abs/pdf links the feed itself gives. Nothing is summarised here; the digest does
that, and it may only say what a record says.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV = "{http://arxiv.org/schemas/atom}"
API = "https://export.arxiv.org/api/query"

# The queries that carry the founder's question. Each one is a mechanism, not a
# keyword: what does the external evidence say about replacing an agent's
# judgement with a machine or a decision model, and when is that replacement wrong?
DEFAULT_QUERIES = [
    ("judge", 'all:"LLM-as-a-judge" AND all:calibration'),
    ("judge-agreement", 'all:"LLM judge" AND all:"human agreement"'),
    ("agentless-ci", 'all:"agentless" AND all:"continuous integration"'),
    ("automated-review", 'all:"automated" AND all:"code review" AND all:"agent"'),
    ("routing", 'all:"routing" AND all:"large language model" AND all:"cost"'),
    ("guardrails", 'all:"guardrails" AND all:"language model" AND all:"formal"'),
    ("overreliance", 'all:"overreliance" AND all:"automation"'),
    ("trajectory-eval", 'all:"trajectory" AND all:"evaluation" AND all:"agent"'),
    ("verifier", 'all:"verifier" AND all:"self-refine" AND all:"language model"'),
    ("workflow-agents", 'all:"durable execution" AND all:"agent"'),
    (
        "spec-driven",
        'all:"formal specification" AND all:"language model" AND all:"code"',
    ),
    (
        "human-loop",
        'all:"human-in-the-loop" AND all:"software development" AND all:"agent"',
    ),
]


def fetch(query: str, max_results: int = 12) -> list[dict]:
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
    )
    url = "{}?{}".format(API, params)
    # S310: the URL is built from API (a constant https://export.arxiv.org/api/query)
    # and urlencode()'d parameters -- there is no scheme to choose and no user input
    # in the path. S314: the body is the Atom feed from that fixed host, and the
    # parser is the standard library on purpose -- the instrument must run on a
    # bare python with no third-party package installed.
    req = urllib.request.Request(  # noqa: S310
        url, headers={"User-Agent": "estate-harvest/1.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        body = resp.read()
    root = ET.fromstring(body)  # noqa: S314
    out = []
    for entry in root.findall("{}entry".format(ATOM)):

        def text(tag, node=entry, ns=ATOM):
            found = node.find(ns + tag)
            return found.text.strip() if found is not None and found.text else None

        cats = [c.get("term") for c in entry.findall("{}category".format(ARXIV))]
        authors = [
            a.findtext("{}name".format(ATOM))
            for a in entry.findall("{}author".format(ATOM))
        ]
        links = {
            l.get("rel"): l.get("href") for l in entry.findall("{}link".format(ARXIV))
        }
        out.append(
            {
                "id": (text("id") or "").rsplit("/", 1)[-1],
                "arxiv_url": text("id"),
                "title": re.sub(r"\s+", " ", text("title") or ""),
                "summary": re.sub(r"\s+", " ", text("summary") or ""),
                "authors": [a for a in authors if a],
                "published": text("published"),
                "updated": text("updated"),
                "categories": cats,
                "primary_category": (text("primary_category", ARXIV) or ""),
                "doi": text("doi", ARXIV),
                "abs": links.get("alternate"),
                "pdf": links.get("related"),
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="-", help="where to write the harvest JSON")
    ap.add_argument("--query", action="append", default=None, help="extra arXiv query")
    ap.add_argument("--max-results", type=int, default=12)
    ap.add_argument("--sleep", type=float, default=3.0)
    ap.add_argument(
        "--verify",
        default=None,
        help="verify a digest cites only records in this harvest file",
    )
    args = ap.parse_args()

    if args.verify:
        return verify(Path(args.verify))

    queries = list(DEFAULT_QUERIES)
    if args.query:
        queries = [("custom:%d" % i, q) for i, q in enumerate(args.query)]

    records: dict[str, dict] = {}
    by_query: dict[str, list[str]] = {}
    for label, q in queries:
        try:
            got = fetch(q, args.max_results)
        except Exception as exc:  # a failed query is reported, never hidden
            print("harvest: query {} failed: {}".format(label, exc), file=sys.stderr)
            by_query[label] = []
            continue
        ids = []
        for rec in got:
            if rec["id"] not in records:
                rec["queries"] = []
                records[rec["id"]] = rec
            records[rec["id"]]["queries"].append(label)
            ids.append(rec["id"])
        by_query[label] = ids
        print("harvest: {} -> {} records".format(label, len(ids)))
        time.sleep(args.sleep)

    payload = {
        "harvested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": API,
        "queries": [{"label": l, "query": q} for l, q in queries],
        "records": sorted(records.values(), key=lambda r: r["id"]),
        "by_query": by_query,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.out == "-":
        sys.stdout.write(text)
    else:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text)
        print(
            "harvest: wrote {} ({} records)".format(args.out, len(payload["records"]))
        )
    return 0


def verify(path: Path) -> int:
    """The falsifier: every arXiv id a digest cites is in the harvest."""
    payload = json.loads(path.read_text())
    known = {re.sub(r"v\d+$", "", r["id"]) for r in payload["records"]}
    cited: set[str] = set()
    # The digest this harvest feeds: the sibling markdown whose name shares the stem. Other
    # digests in the directory belong to other harvests and are not this file's business.
    stem = path.stem.replace("-harvest", "")
    digests = sorted(path.parent.glob("{}*.md".format(stem)))
    if not digests:
        print("verify: no digest sibling for {}".format(path.name))
        return 1
    for other in digests:
        cited |= set(
            re.findall(r"\b\d{4}\.\d{4,5}\b", other.read_text(errors="replace"))
        )
    missing = sorted(cited - known)
    for mid in missing:
        print("verify: CITED BUT NOT HARVESTED: {}".format(mid))
    print(
        "verify: {} records, {} cited ids, {} missing".format(
            len(known), len(cited), len(missing)
        )
    )
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
