#!/usr/bin/env python3
"""
CN Paper Downloader: Scrape PDFs and peer review attachments from Magtech-based Chinese journals.
Supports journal.psych.ac.cn and similar Magtech CMS journals.

Usage:
  python scrape.py --journal xlxb --output D:/papers --latest
  python scrape.py --journal xlkxjz --output D:/papers --from 2024-01 --to 2025-12
  python scrape.py --journal xlxb --output D:/papers --resume
"""

import argparse
import io
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

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

DELAY = 1.5  # seconds between requests


# ── HTTP helpers ──────────────────────────────────────────────────────────────
def get(url, http_client, retries=3):
    for i in range(retries):
        try:
            r = http_client.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r
        except Exception as e:
            if i == retries - 1:
                raise
            print(f"  Retry {i+1}/{retries} for {url}: {e}")
            time.sleep(2)


def download_binary(url, dest_path, http_client, referer=None):
    h = dict(HEADERS)
    if referer:
        h["Referer"] = referer
    r = http_client.get(url, headers=h, timeout=60, stream=True)
    r.raise_for_status()
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    return dest_path.stat().st_size


# ── Parsing ───────────────────────────────────────────────────────────────────
def parse_issue_list(base_url, http_client):
    """Return list of (year, vol, issue_no, volumn_url) sorted newest-first."""
    url = f"{base_url}/CN/article/showOldVolumn.do"
    soup = BeautifulSoup(get(url, http_client).text, "html.parser")
    issues = []
    # Pattern: ../volumn/volumn_NNN.shtml  with text like "No.2"
    # Year rows are in table cells before the issue links
    current_year = None
    for td in soup.find_all(["td", "th"]):
        text = td.get_text(strip=True)
        # Detect year row: "2026 Vol.58"
        m = re.match(r"(\d{4})\s+Vol\.(\d+)", text)
        if m:
            current_year = int(m.group(1))
            continue
        # Detect issue link
        a = td.find("a", href=re.compile(r"volumn/volumn_\d+\.shtml"))
        if a and current_year:
            href = a["href"]
            volumn_url = urljoin(base_url + "/CN/", href.lstrip("../"))
            issue_text = a.get_text(strip=True)  # e.g. "No.3" or "No.suppl."
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

    # Article ID from citation_pdf_url meta tag
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if not meta:
        return None
    pdf_meta_url = meta["content"]
    m = re.search(r"id=(\d+)", pdf_meta_url)
    if not m:
        return None
    article_id = m.group(1)

    # Title
    title_tag = soup.find("meta", attrs={"name": "citation_title"})
    title = title_tag["content"].strip() if title_tag else f"article_{article_id}"

    # Authors
    author_tags = soup.find_all("meta", attrs={"name": "citation_author"})
    authors = ", ".join(t["content"] for t in author_tags) if author_tags else ""

    # DOI
    doi_tag = soup.find("meta", attrs={"name": "citation_doi"})
    doi = doi_tag["content"].strip() if doi_tag else ""

    # Peer review attachment link (审稿意见 / PSFJ)
    review_url = None
    review_a = soup.find("a", href=re.compile(r"attachType=PSFJ"))
    if review_a:
        href = review_a["href"]
        if href.startswith("http"):
            review_url = href
        else:
            # href is relative to the article page, e.g. "../article/downloadArticleFile.do?..."
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
    """
    output_root/journal_code/year/issue_no/article_id_title/
    """
    folder_name = f"{article_id}_{safe_name(title)}"
    return Path(output_root) / journal_code / str(year) / issue_no / folder_name


# ── Checkpoint ────────────────────────────────────────────────────────────────
def load_checkpoint(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"completed_article_ids": [], "completed_issues": []}


def save_checkpoint(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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

    # ── Get issue list ────────────────────────────────────────────────────────
    print("\nFetching issue list...")
    all_issues = parse_issue_list(base_url, http_client)
    time.sleep(DELAY)

    # ── Filter by date range ──────────────────────────────────────────────────
    if args.latest:
        issues_to_scrape = all_issues[:1]
    else:
        from_year = int(args.from_date.split("-")[0]) if args.from_date else 0
        from_month_str = args.from_date if args.from_date else None
        to_year = int(args.to_date.split("-")[0]) if args.to_date else 9999
        to_month_str = args.to_date if args.to_date else None

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
            print(f"  Skip (done): {year} {issue_no}")
            continue

        print(f"\n── {year} {issue_no} ──")
        article_urls = parse_articles_from_issue(volumn_url, http_client)
        time.sleep(DELAY)
        print(f"  Articles: {len(article_urls)}")

        for art_url in article_urls:
            # ── Parse article page ────────────────────────────────────────
            try:
                info = parse_article_page(art_url, http_client)
                time.sleep(DELAY)
            except Exception as e:
                print(f"  ERROR parsing {art_url}: {e}")
                continue

            if not info:
                print(f"  SKIP (no PDF meta): {art_url}")
                continue

            aid = info["article_id"]
            if aid in cp["completed_article_ids"]:
                print(f"  Skip (done): {info['title'][:40]}")
                continue

            dest_dir = article_dir(output_root, args.journal, year, issue_no, aid, info["title"])

            # ── Download PDF ──────────────────────────────────────────────
            pdf_path = dest_dir / f"{aid}.pdf"
            if not pdf_path.exists():
                try:
                    size = download_binary(info["pdf_url"], pdf_path, http_client, referer=art_url)
                    print(f"  PDF  {info['title'][:40]} ({size//1024}KB)")
                    time.sleep(DELAY)
                except Exception as e:
                    print(f"  ERROR PDF {aid}: {e}")

            # ── Download peer review attachment ───────────────────────────
            if info["review_url"]:
                review_path = dest_dir / f"{aid}_review.pdf"
                if not review_path.exists():
                    try:
                        size = download_binary(info["review_url"], review_path, http_client, referer=art_url)
                        print(f"  Review {info['title'][:40]} ({size//1024}KB)")
                        time.sleep(DELAY)
                    except Exception as e:
                        print(f"  WARN review {aid}: {e}")

            # ── Save metadata ─────────────────────────────────────────────
            meta = {**info, "year": year, "issue": issue_no, "journal": args.journal}
            with open(meta_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(meta, ensure_ascii=False) + "\n")

            cp["completed_article_ids"].append(aid)
            save_checkpoint(checkpoint_path, cp)

        cp["completed_issues"].append(issue_key)
        save_checkpoint(checkpoint_path, cp)
        print(f"  Issue {issue_key} complete.")

    print("\nDone.")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Scrape PDFs from Magtech Chinese journals")
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
    parser.add_argument("--resume", action="store_true",
                        help="Resume from checkpoint (default behavior, flag is informational)")
    args = parser.parse_args()

    if not args.latest and not args.from_date and not args.to_date:
        print("Specify --latest, or --from/--to date range.")
        sys.exit(1)

    scrape(args)


if __name__ == "__main__":
    main()
