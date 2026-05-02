#!/usr/bin/env python3
"""
CN Paper Downloader v2: High-performance PDF scraper with concurrent downloads.
Supports journal.psych.ac.cn and similar Magtech CMS journals.

Usage:
  python scrape_v2.py --journal xlxb --output D:/papers --latest
  python scrape_v2.py --journal xlkxjz --output D:/papers --from 2024-01 --to 2025-12
  python scrape_v2.py --journal xlxb --output D:/papers --from 2010-01 --workers 5
"""

import argparse
import io
import json
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from queue import Queue

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from bs4 import BeautifulSoup

# ── Journal registry ──────────────────────────────────────────────────────────
JOURNALS = {
    "xlxb": {
        "name": "心理学报",
        "base_url": "https://journal.psych.ac.cn/xlxb",
    },
    "xlkxjz": {
        "name": "心理科学进展",
        "base_url": "https://journal.psych.ac.cn/xlkxjz",
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

DEFAULT_DELAY = 1.0  # seconds between requests (reduced with workers)
TIMEOUT_PAGE = 30    # seconds for page requests
TIMEOUT_DOWNLOAD = 120  # seconds for PDF downloads

# Thread-safe locks
print_lock = threading.Lock()
checkpoint_lock = threading.Lock()
meta_lock = threading.Lock()

# ── Progress display ──────────────────────────────────────────────────────────
class ProgressTracker:
    def __init__(self):
        self.total = 0
        self.completed = 0
        self.failed = 0
        self.skipped = 0
        self.lock = threading.Lock()
        self.start_time = time.time()

    def set_total(self, n):
        with self.lock:
            self.total = n
            self._print()

    def inc_completed(self):
        with self.lock:
            self.completed += 1
            self._print()

    def inc_failed(self):
        with self.lock:
            self.failed += 1
            self._print()

    def inc_skipped(self):
        with self.lock:
            self.skipped += 1
            self._print()

    def _print(self):
        elapsed = time.time() - self.start_time
        rate = self.completed / elapsed if elapsed > 0 else 0
        with print_lock:
            print(f"\r  Progress: {self.completed}/{self.total} "
                  f"(skipped:{self.skipped}, failed:{self.failed}) "
                  f"[{rate:.1f} articles/s]", end="", flush=True)

    def finish(self):
        with print_lock:
            print()  # New line after progress

progress = ProgressTracker()

# ── HTTP helpers ──────────────────────────────────────────────────────────────
def get(url, http_client, retries=3, timeout=TIMEOUT_PAGE):
    """Fetch URL with retries and exponential backoff."""
    for i in range(retries):
        try:
            r = http_client.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            if i == retries - 1:
                raise
            wait = 2 ** i  # 1, 2, 4 seconds
            with print_lock:
                print(f"\n  Retry {i+1}/{retries} for {url}: {e}")
            time.sleep(wait)


def download_binary(url, dest_path, http_client, referer=None, timeout=TIMEOUT_DOWNLOAD):
    """Download binary file with streaming."""
    h = dict(HEADERS)
    if referer:
        h["Referer"] = referer
    r = http_client.get(url, headers=h, timeout=timeout, stream=True)
    r.raise_for_status()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(65536):  # 64KB chunks
            f.write(chunk)
    return dest_path.stat().st_size


# ── Parsing ───────────────────────────────────────────────────────────────────
def parse_issue_list(base_url, http_client):
    """Return list of (year, vol, issue_no, volumn_url) sorted newest-first."""
    url = f"{base_url}/CN/article/showOldVolumn.do"
    soup = BeautifulSoup(get(url, http_client).text, "html.parser")
    issues = []
    current_year = None
    for td in soup.find_all(["td", "th"]):
        text = td.get_text(strip=True)
        m = re.match(r"(\d{4})\s+Vol\.(\d+)", text)
        if m:
            current_year = int(m.group(1))
            continue
        a = td.find("a", href=re.compile(r"volumn/volumn_\d+\.shtml"))
        if a and current_year:
            href = a["href"]
            volumn_url = urljoin(base_url + "/CN/", href.lstrip("../"))
            issue_text = a.get_text(strip=True)
            issues.append((current_year, volumn_url, issue_text))
    return issues


def parse_articles_from_issue(volumn_url, http_client):
    """Return list of article DOI URLs from an issue page."""
    soup = BeautifulSoup(get(volumn_url, http_client).text, "html.parser")
    articles = []
    for a in soup.find_all("a", href=re.compile(r"/CN/10\.\d{4}/")):
        href = a["href"]
        if href.startswith("http"):
            articles.append(href)
        else:
            base = re.match(r"(https?://[^/]+)", volumn_url).group(1)
            articles.append(base + href)
    # Deduplicate while preserving order
    seen = set()
    result = []
    for u in articles:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


def parse_article_page(article_url, http_client):
    """
    Return dict with keys: article_id, title, authors, doi, pdf_url, review_url (may be None).
    """
    soup = BeautifulSoup(get(article_url, http_client).text, "html.parser")

    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if not meta:
        return None
    pdf_meta_url = meta["content"]
    m = re.search(r"id=(\d+)", pdf_meta_url)
    if not m:
        return None
    article_id = m.group(1)

    title_tag = soup.find("meta", attrs={"name": "citation_title"})
    title = title_tag["content"].strip() if title_tag else f"article_{article_id}"

    author_tags = soup.find_all("meta", attrs={"name": "citation_author"})
    authors = ", ".join(t["content"] for t in author_tags) if author_tags else ""

    doi_tag = soup.find("meta", attrs={"name": "citation_doi"})
    doi = doi_tag["content"].strip() if doi_tag else ""

    review_url = None
    review_a = soup.find("a", href=re.compile(r"attachType=PSFJ"))
    if review_a:
        href = review_a["href"]
        if href.startswith("http"):
            review_url = href
        else:
            review_url = urljoin(article_url, href)

    return {
        "article_id": article_id,
        "title": title,
        "authors": authors,
        "doi": doi,
        "pdf_url": pdf_meta_url,
        "review_url": review_url,
        "article_url": article_url,
    }


# ── File naming ───────────────────────────────────────────────────────────────
def safe_name(s, max_len=60):
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s[:max_len]


def article_dir(output_root, journal_code, year, issue_no, article_id, title):
    folder_name = f"{article_id}_{safe_name(title)}"
    return Path(output_root) / journal_code / str(year) / issue_no / folder_name


# ── Checkpoint ────────────────────────────────────────────────────────────────
def load_checkpoint(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"completed_article_ids": [], "completed_issues": []}


def save_checkpoint(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with checkpoint_lock:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_metadata(meta_log_path, meta):
    """Thread-safe metadata append."""
    with meta_lock:
        with open(meta_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")


# ── Article download worker ───────────────────────────────────────────────────
def download_article(args_tuple):
    """
    Worker function to download a single article.
    Returns: (article_id, success: bool, error_msg: str)
    """
    article_url, info, output_root, journal_code, year, issue_no, checkpoint_path, cp, meta_log_path, http_client = args_tuple

    aid = info["article_id"]

    # Check if already completed
    if aid in cp["completed_article_ids"]:
        progress.inc_skipped()
        return (aid, True, "Already downloaded")

    dest_dir = article_dir(output_root, journal_code, year, issue_no, aid, info["title"])

    # Download PDF
    pdf_path = dest_dir / f"{aid}.pdf"
    if not pdf_path.exists():
        try:
            size = download_binary(info["pdf_url"], pdf_path, http_client, referer=article_url)
            with print_lock:
                print(f"\n  [OK] PDF {info['title'][:50]} ({size//1024}KB)")
        except Exception as e:
            progress.inc_failed()
            with print_lock:
                print(f"\n  [ERROR] PDF {aid}: {e}")
            return (aid, False, str(e))

    # Download peer review attachment
    if info["review_url"]:
        review_path = dest_dir / f"{aid}_review.pdf"
        if not review_path.exists():
            try:
                size = download_binary(info["review_url"], review_path, http_client, referer=article_url)
                with print_lock:
                    print(f"\n  [OK] Review {info['title'][:50]} ({size//1024}KB)")
            except Exception as e:
                with print_lock:
                    print(f"\n  [WARN] Review {aid}: {e}")

    # Save metadata
    meta = {**info, "year": year, "issue": issue_no, "journal": journal_code}
    append_metadata(meta_log_path, meta)

    # Update checkpoint
    cp["completed_article_ids"].append(aid)
    save_checkpoint(checkpoint_path, cp)

    progress.inc_completed()
    return (aid, True, None)


# ── Main scrape logic ─────────────────────────────────────────────────────────
def scrape(args):
    journal = JOURNALS[args.journal]
    base_url = journal["base_url"]
    output_root = Path(args.output)
    checkpoint_path = output_root / args.journal / ".checkpoint.json"

    http_client = requests.Session()
    cp = load_checkpoint(checkpoint_path)

    print(f"Journal: {journal['name']} ({args.journal})")
    print(f"Output:  {output_root / args.journal}")
    print(f"Workers: {args.workers}")

    # ── Get issue list ────────────────────────────────────────────────────────
    print("\nFetching issue list...")
    try:
        all_issues = parse_issue_list(base_url, http_client)
    except Exception as e:
        print(f"ERROR: Failed to fetch issue list: {e}")
        sys.exit(1)
    time.sleep(DEFAULT_DELAY)

    # ── Filter by date range ──────────────────────────────────────────────────
    if args.latest:
        issues_to_scrape = all_issues[:1]
    else:
        from_year = int(args.from_date.split("-")[0]) if args.from_date else 0
        to_year = int(args.to_date.split("-")[0]) if args.to_date else 9999

        issues_to_scrape = []
        for year, volumn_url, issue_no in all_issues:
            if year < from_year or year > to_year:
                continue
            issues_to_scrape.append((year, volumn_url, issue_no))

    print(f"Issues to scrape: {len(issues_to_scrape)}")

    # ── Metadata log ─────────────────────────────────────────────────────────
    meta_log_path = output_root / args.journal / "metadata.jsonl"
    meta_log_path.parent.mkdir(parents=True, exist_ok=True)

    # ── Iterate issues ────────────────────────────────────────────────────────
    for year, volumn_url, issue_no in issues_to_scrape:
        issue_key = f"{year}_{issue_no}"
        if issue_key in cp["completed_issues"]:
            print(f"\n[SKIP] {year} {issue_no} (already completed)")
            continue

        print(f"\n{'='*60}")
        print(f"Processing: {year} {issue_no}")
        print(f"{'='*60}")

        # Get article URLs for this issue
        try:
            article_urls = parse_articles_from_issue(volumn_url, http_client)
            time.sleep(DEFAULT_DELAY)
        except Exception as e:
            print(f"[ERROR] Failed to parse issue page: {e}")
            continue

        print(f"Found {len(article_urls)} articles")

        # Parse all article pages first (sequential to be polite)
        articles_to_download = []
        for art_url in article_urls:
            try:
                info = parse_article_page(art_url, http_client)
                time.sleep(DEFAULT_DELAY / args.workers)  # Reduced delay with workers
            except Exception as e:
                print(f"\n[ERROR] Parsing {art_url}: {e}")
                continue

            if not info:
                print(f"\n[WARN] No PDF metadata: {art_url}")
                continue

            if info["article_id"] in cp["completed_article_ids"]:
                continue

            articles_to_download.append((art_url, info))

        print(f"New articles to download: {len(articles_to_download)}")
        if not articles_to_download:
            cp["completed_issues"].append(issue_key)
            save_checkpoint(checkpoint_path, cp)
            print(f"[DONE] {issue_key} (all articles already downloaded)")
            continue

        # Download articles concurrently
        progress.set_total(len(articles_to_download))
        progress.start_time = time.time()

        # Prepare worker arguments
        worker_args = [
            (art_url, info, output_root, args.journal, year, issue_no,
             checkpoint_path, cp, meta_log_path, http_client)
            for art_url, info in articles_to_download
        ]

        # Execute concurrent downloads
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(download_article, arg): arg for arg in worker_args}
            for future in as_completed(futures):
                try:
                    aid, success, msg = future.result()
                except Exception as e:
                    progress.inc_failed()
                    with print_lock:
                        print(f"\n[ERROR] Unexpected error: {e}")

        progress.finish()

        # Mark issue as complete
        cp["completed_issues"].append(issue_key)
        save_checkpoint(checkpoint_path, cp)
        print(f"[DONE] {issue_key}")

    print(f"\n{'='*60}")
    print("Scraping complete!")
    print(f"{'='*60}")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="High-performance PDF scraper for Magtech Chinese journals"
    )
    parser.add_argument("--journal", required=True, choices=list(JOURNALS.keys()),
                        help="Journal code, e.g. xlxb or xlkxjz")
    parser.add_argument("--output", required=True,
                        help="Root output directory, e.g. D:/papers")
    parser.add_argument("--latest", action="store_true",
                        help="Only scrape the latest issue")
    parser.add_argument("--from", dest="from_date", default=None,
                        help="Start year-month, e.g. 2024-01")
    parser.add_argument("--to", dest="to_date", default=None,
                        help="End year-month, e.g. 2025-12")
    parser.add_argument("--workers", type=int, default=3,
                        help="Number of concurrent download workers (default: 3)")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help=f"Delay between requests in seconds (default: {DEFAULT_DELAY})")
    args = parser.parse_args()

    if not args.latest and not args.from_date and not args.to_date:
        print("Specify --latest, or --from/--to date range.")
        sys.exit(1)

    scrape(args)


if __name__ == "__main__":
    main()
