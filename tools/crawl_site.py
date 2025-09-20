#!/usr/bin/env python3
"""
Lightweight site crawler to enumerate URLs and collect basic metadata.

Features:
- Fetches robots.txt and respects disallow rules (optional)
- Attempts to parse /sitemap.xml and /sitemap_index.xml
- Crawls internal links up to a max depth
- Collects title, meta description, first H1, status, content-type
- Records discovered assets (img, script, link href)

Usage:
  python tools/crawl_site.py --start-url https://example.com --max-depth 3 --max-pages 200
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from typing import Dict, List, Optional, Set, Tuple


def normalize_url(url: str) -> str:
    # Remove fragments, normalize scheme/host casing, strip trailing slash except root
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    # Remove duplicate slashes in path
    path = re.sub(r"/+", "/", path)
    # Normalize trailing slash (keep for root only)
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")
    query = parsed.query
    return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))


def same_host(u1: str, u2: str) -> bool:
    return urllib.parse.urlsplit(u1).netloc.lower() == urllib.parse.urlsplit(u2).netloc.lower()


def guess_is_asset(url: str) -> bool:
    return any(
        url.lower().endswith(ext)
        for ext in (
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".svg",
            ".ico",
            ".css",
            ".js",
            ".map",
            ".woff",
            ".woff2",
            ".ttf",
            ".otf",
            ".eot",
            ".pdf",
            ".zip",
            ".gz",
        )
    )


@dataclass
class PageInfo:
    url: str
    status: Optional[int] = None
    content_type: Optional[str] = None
    title: Optional[str] = None
    h1: Optional[str] = None
    description: Optional[str] = None
    links: List[str] = None
    assets: List[str] = None
    from_sitemap: bool = False


class LinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: Set[str] = set()
        self.assets: Set[str] = set()
        self.in_title = False
        self.title: List[str] = []
        self.h1: List[str] = []
        self.in_h1 = False
        self.meta_description: Optional[str] = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        def add_url(attr_name: str, is_asset: bool = False):
            val = attrs_dict.get(attr_name)
            if not val:
                return
            abs_url = urllib.parse.urljoin(self.base_url, val)
            if is_asset or guess_is_asset(abs_url):
                self.assets.add(abs_url)
            else:
                self.links.add(abs_url)

        if tag == "a":
            add_url("href")
        elif tag == "link":
            add_url("href", is_asset=True)
        elif tag in ("script", "img", "source", "video", "audio", "iframe"):
            add_url("src", is_asset=True)
        elif tag == "form":
            add_url("action")
        elif tag == "meta":
            name = (attrs_dict.get("name") or attrs_dict.get("property") or "").lower()
            if name == "description" and not self.meta_description:
                self.meta_description = attrs_dict.get("content")
        elif tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.in_h1 = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "h1":
            self.in_h1 = False

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data.strip())
        if self.in_h1:
            self.h1.append(data.strip())


def http_get(url: str, user_agent: str, timeout: int = 15) -> Tuple[Optional[int], Dict[str, str], bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            headers = {k.lower(): v for k, v in resp.headers.items()}
            data = resp.read()
            # Decompress if gz
            if headers.get("content-encoding", "").lower() == "gzip":
                try:
                    data = gzip.decompress(data)
                except Exception:
                    pass
            return status, headers, data
    except Exception as e:
        return None, {}, b""


def parse_sitemaps(base_url: str, user_agent: str) -> Set[str]:
    urls: Set[str] = set()
    candidates = [urllib.parse.urljoin(base_url, p) for p in ("/sitemap.xml", "/sitemap_index.xml")]
    for sm_url in candidates:
        status, headers, body = http_get(sm_url, user_agent)
        if not status or status >= 400 or not body:
            continue
        ct = headers.get("content-type", "")
        text = body.decode("utf-8", errors="ignore")
        # Very light-weight XML extraction for <loc>...</loc>
        for m in re.finditer(r"<loc>\s*([^<]+)\s*</loc>", text, flags=re.IGNORECASE):
            loc = m.group(1).strip()
            # Some sitemaps contain HTML pages and asset links alike
            urls.add(loc)
    return urls


def load_robots(base_url: str, user_agent: str) -> urllib.robotparser.RobotFileParser:
    rp = urllib.robotparser.RobotFileParser()
    robots_url = urllib.parse.urljoin(base_url, "/robots.txt")
    try:
        rp.set_url(robots_url)
        rp.read()
    except Exception:
        pass
    return rp


def crawl(start_url: str, max_depth: int, max_pages: int, same_domain_only: bool, respect_robots: bool, delay: float, user_agent: str) -> Dict[str, PageInfo]:
    start_url = normalize_url(start_url)
    origin = f"{urllib.parse.urlsplit(start_url).scheme}://{urllib.parse.urlsplit(start_url).netloc}"
    allowed_host = urllib.parse.urlsplit(start_url).netloc

    rp = load_robots(origin, user_agent) if respect_robots else None
    from_sitemap = parse_sitemaps(origin, user_agent)

    queue = collections.deque([(start_url, 0)])
    for sm in from_sitemap:
        if same_domain_only and urllib.parse.urlsplit(sm).netloc != allowed_host:
            continue
        queue.append((normalize_url(sm), 0))

    visited: Set[str] = set()
    results: Dict[str, PageInfo] = {}

    while queue and len(visited) < max_pages:
        url, depth = queue.popleft()
        url = normalize_url(url)
        if url in visited:
            continue
        if same_domain_only and urllib.parse.urlsplit(url).netloc != allowed_host:
            continue
        if respect_robots and rp and not rp.can_fetch(user_agent, url):
            continue

        visited.add(url)
        status, headers, body = http_get(url, user_agent)

        ct = headers.get("content-type", "")
        pi = PageInfo(url=url, status=status, content_type=ct, links=[], assets=[], from_sitemap=(url in from_sitemap))

        # Only parse HTML pages
        if status and status < 400 and body and ("text/html" in ct or (ct == "" and body.startswith(b"<!DOCTYPE html"))):
            text = body.decode("utf-8", errors="ignore")
            parser = LinkParser(url)
            try:
                parser.feed(text)
            except Exception:
                pass
            pi.title = (" ".join(parser.title)).strip() or None
            pi.h1 = (" ".join(parser.h1)).strip() or None
            pi.description = parser.meta_description

            # Normalize and filter links
            links = set()
            for href in parser.links:
                if not href:
                    continue
                # Skip mailto/tel/javascript
                if href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:"):
                    continue
                abs_url = normalize_url(href)
                if same_domain_only and not same_host(abs_url, start_url):
                    continue
                links.add(abs_url)
            pi.links = sorted(links)

            assets = set()
            for src in parser.assets:
                if not src:
                    continue
                assets.add(normalize_url(src))
            pi.assets = sorted(assets)

            # Enqueue links for crawling
            if depth < max_depth:
                for nxt in pi.links:
                    if nxt not in visited:
                        queue.append((nxt, depth + 1))

        results[url] = pi
        if delay > 0:
            time.sleep(delay)

    return results


def to_csv(results: Dict[str, PageInfo], out_path: str):
    cols = [
        "url",
        "status",
        "content_type",
        "title",
        "h1",
        "description",
        "from_sitemap",
        "links_count",
        "assets_count",
    ]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for pi in results.values():
            w.writerow([
                pi.url,
                pi.status if pi.status is not None else "",
                pi.content_type or "",
                (pi.title or "").strip(),
                (pi.h1 or "").strip(),
                (pi.description or "").strip(),
                "yes" if pi.from_sitemap else "no",
                len(pi.links or []),
                len(pi.assets or []),
            ])


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-url", default="https://testathon.live/")
    ap.add_argument("--max-depth", type=int, default=3)
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--same-domain-only", action="store_true", default=True)
    ap.add_argument("--all-domains", dest="same_domain_only", action="store_false", help="Allow cross-domain links")
    ap.add_argument("--respect-robots", action="store_true", default=True)
    ap.add_argument("--no-robots", dest="respect_robots", action="store_false", help="Ignore robots.txt")
    ap.add_argument("--delay", type=float, default=0.2)
    ap.add_argument("--user-agent", default="Mozilla/5.0 (compatible; CodexCrawler/1.0; +https://openai.com)")
    ap.add_argument("--out-json", default="crawl_results.json")
    ap.add_argument("--out-csv", default="crawl_results.csv")
    args = ap.parse_args(argv)

    results = crawl(
        start_url=args.start_url,
        max_depth=args.max_depth,
        max_pages=args.max_pages,
        same_domain_only=args.same_domain_only,
        respect_robots=args.respect_robots,
        delay=args.delay,
        user_agent=args.user_agent,
    )

    # Write JSON
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump({k: asdict(v) for k, v in results.items()}, f, ensure_ascii=False, indent=2)

    # Write CSV
    to_csv(results, args.out_csv)

    # Also print a small summary to stdout
    pages = [p for p in results.values() if p.content_type and "text/html" in p.content_type]
    print(f"Crawled {len(results)} URLs (HTML pages: {len(pages)}). Output: {args.out_json}, {args.out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
