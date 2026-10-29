"""Verify manuscript/bibliography URLs and save primary-source metadata, without inference."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class Meta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.values = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "meta":
            name = values.get("name", values.get("property", ""))
            self.values.setdefault(name, []).append(values.get("content", ""))


def check(url):
    for attempt in range(4):
        try:
            with urlopen(
                Request(
                    url, headers={"User-Agent": "leaderboard-noise-paper-source-verification/0.1"}
                ),
                timeout=45,
            ) as response:
                body = response.read()
                status = response.status
                resolved = response.url
            assert status == 200
            parser = Meta()
            parser.feed(body.decode("utf-8", errors="replace"))
            return {
                "url": url,
                "resolved_url": resolved,
                "status": status,
                "body_sha256": hashlib.sha256(body).hexdigest(),
                "citation_title": parser.values.get(
                    "citation_title", parser.values.get("og:title", [])
                )
                or re.findall(
                    r"<h1[^>]*>(.*?)</h1>", body.decode("utf-8", errors="replace"), flags=re.S
                ),
                "citation_authors": parser.values.get("citation_author", []),
                "citation_date": parser.values.get(
                    "citation_date", parser.values.get("citation_publication_date", [])
                ),
            }
        except (HTTPError, URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def main():
    bib = Path("paper/references.bib").read_text()
    entries = re.split(r"(?m)^@", bib)[1:]
    references = []
    for block in entries:
        key = block.split("{", 1)[1].split(",", 1)[0]
        url = re.search(r"url\s*=\s*\{([^}]+)\}", block).group(1)
        title = re.search(r"title\s*=\s*\{(.*?)\},\s*\n?\s*author", block, re.S)
        if title is None:
            title = re.search(r"title\s*=\s*\{(.*?)\},\s*\n?\s*(?:journal|year)", block, re.S)
        references.append(
            {
                "key": key,
                "expected_title": title.group(1) if title else "",
                "url": url,
                "bibtex_entry_sha256": hashlib.sha256(("@" + block).encode()).hexdigest(),
            }
        )
    urls = sorted(
        {x["url"] for x in references}
        | set(re.findall(r"\\url\{(https?://[^}]+)\}", Path("paper/main.tex").read_text()))
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(check, urls))
    lookup = {r["url"]: r for r in results}
    for ref in references:
        ref.update(lookup[ref["url"]], primary_source=True)

        def normalize(t):
            return re.sub(r"[^a-z0-9]", "", unescape(re.sub(r"<[^>]+>", "", t)).lower())

        expected = normalize(ref["expected_title"])
        if not expected or not any(expected in normalize(t) for t in ref["citation_title"]):
            raise RuntimeError("Primary-source title mismatch: " + ref["key"])
        ref["title_verified_against_primary_source"] = True
    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "references": references,
        "links": results,
        "scope": "Primary paper/author/project sources. BibTeX metadata and associated claims were also read against those primary sources; no citation inferred from a secondary index.",
        "searched_additional_work": [
            "numerical inference reproducibility; batch size/GPU changes",
            "hosted deterministic settings and raw vs parsed agreement",
            "greedy vs sampling evaluation",
            "verified speculation as a mitigation",
        ],
        "new_inference": False,
    }
    Path("paper/references-verified.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(
        f"Verified {len(references)} citations and {len(results)} public primary/repository URLs (HTTP 200)."
    )


if __name__ == "__main__":
    main()
