#!/usr/bin/env python3
"""
download_lutheran_hymn_sheet_music.py

Downloads sheet‑music PDFs for a list of Lutheran hymns from IMSLP.org.

Author: <your name or open‑source community>
License: MIT / public domain (as per IMSLP policy)
"""

import os
import sys
import time
import logging
import pathlib
import urllib.parse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# --------------------------------------------------------------------------- #
# Configuration – edit these values before running
# --------------------------------------------------------------------------- #

# List of hymn titles.  Use the English title (or any title that is known to
# appear on IMSLP).  Feel free to add/remove titles.
HYMNS = [
    "Annie Laurie",          # example of a popular public‑domain hymn
    "Rock Of Ages",
    "The Old Rugged Cross",
    "Amazing Grace",
    "Blessed Assurance",
    "Crown Him with Many Crowns",
    # ... add as many as you want
]

# Directory that will hold the downloaded PDFs
OUT_DIR = pathlib.Path("lutheran_hymn_scores")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Minimum time (in seconds) to wait between requests – keeps us polite to IMSLP
MIN_DELAY = 1.5

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

HEADERS = {
    "User-Agent": (
        "LutheranHymnDownloader/1.0 "
        "(https://github.com/yourrepo/yourproject; contact: your@email)"
    )
}


def safe_sleep(previous_time):
    """Sleep to respect MIN_DELAY between consecutive requests."""
    elapsed = time.time() - previous_time
    if elapsed < MIN_DELAY:
        time.sleep(MIN_DELAY - elapsed)


def build_score_page_url(title: str) -> str:
    """Construct the likely IMSLP score page URL for a given title."""
    # IMSLP uses underscores in URLs.  Replace spaces and strip punctuation.
    safe_title = title.replace(" ", "_")
    return f"https://imslp.org/wiki/{safe_title}"


def fetch(url: str, session: requests.Session) -> requests.Response:
    """GET a URL, following redirects, and return the Response object."""
    response = session.get(url, headers=HEADERS)
    response.raise_for_status()
    return response


def find_pdf_link(soup: BeautifulSoup) -> str | None:
    """
    Look for the first PDF link on an IMSLP score page.
    Returns the absolute URL or None if not found.
    """
    # The PDF link is usually a <a> tag that ends with ".pdf"
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            return urllib.parse.urljoin("https://imslp.org", href)
    return None


def download_pdf(pdf_url: str, dest_path: pathlib.Path, session: requests.Session):
    """Download a PDF file to the destination path."""
    with session.get(pdf_url, headers=HEADERS, stream=True) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


# --------------------------------------------------------------------------- #
# Main logic
# --------------------------------------------------------------------------- #

def main():
    session = requests.Session()

    last_request_time = time.time() - MIN_DELAY  # so first request goes straight through

    for hymn in tqdm(HYMNS, desc="Processing hymns"):
        safe_sleep(last_request_time)
        last_request_time = time.time()

        score_page_url = build_score_page_url(hymn)
        logging.info(f"Searching for hymn page: {score_page_url}")

        try:
            resp = fetch(score_page_url, session)
        except requests.HTTPError as exc:
            logging.warning(f"Could not fetch page for '{hymn}': {exc}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")

        pdf_link = find_pdf_link(soup)
        if not pdf_link:
            logging.warning(f"No PDF link found for '{hymn}'.")
            continue

        logging.info(f"Found PDF: {pdf_link}")

        # Create a file‑friendly name
        safe_name = "_".join(part for part in hymn.split() if part.isalnum())
        dest_file = OUT_DIR / f"{safe_name}.pdf"

        try:
            download_pdf(pdf_link, dest_file, session)
            logging.info(f"Downloaded to: {dest_file}")
        except requests.HTTPError as exc:
            logging.error(f"Failed to download PDF for '{hymn}': {exc}")

    logging.info("All done. PDF files are in: %s", OUT_DIR)


if __name__ == "__main__":
    main()
