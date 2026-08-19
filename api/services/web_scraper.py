import html.parser
import os
import re
import ssl
import urllib.parse
from typing import List, Tuple

import httpx

from api.core.logging import get_logger

logger = get_logger(__name__)


class HTMLTextExtractor(html.parser.HTMLParser):
    """Clean HTML parser that extracts text and internal subpage links."""

    def __init__(self, base_url: str = "") -> None:
        super().__init__()
        self.base_url = base_url
        self.text_parts: List[str] = []
        self.found_links: List[str] = []
        self.ignore_tag = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "head", "noscript", "svg", "path"):
            self.ignore_tag = True
        elif tag in ("p", "h1", "h2", "h3", "h4", "li", "tr", "div"):
            self.text_parts.append("\n")

        if tag == "a":
            for attr_name, attr_val in attrs:
                if attr_name == "href" and attr_val:
                    full_url = urllib.parse.urljoin(self.base_url, attr_val)
                    if full_url.startswith("http"):
                        self.found_links.append(full_url)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "head", "noscript", "svg", "path"):
            self.ignore_tag = False
        elif tag in ("p", "h1", "h2", "h3", "h4", "li", "tr", "div"):
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.ignore_tag:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned + " ")

    def get_clean_text(self) -> str:
        raw_text = "".join(self.text_parts)
        cleaned = re.sub(r"\n\s*\n+", "\n\n", raw_text)
        return cleaned.strip()


async def fetch_web_page_and_links(url: str) -> Tuple[str, List[str]]:
    """Fetch URL over HTTP, extract clean text content, and discover subpage links."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36 ColigoScraper/1.0"
        )
    }
    logger.info("scraping_url_start", url=url)

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    try:
        ssl_context.set_ciphers("DEFAULT@SECLEVEL=1")
    except Exception:
        pass

    async with httpx.AsyncClient(
        follow_redirects=True, timeout=20.0, verify=ssl_context
    ) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()

    parser = HTMLTextExtractor(base_url=url)
    parser.feed(response.text)
    extracted_text = parser.get_clean_text()

    # Filter subpage links to keep only those on the same domain
    domain = urllib.parse.urlparse(url).netloc
    same_domain_links = list(
        dict.fromkeys(
            link
            for link in parser.found_links
            if urllib.parse.urlparse(link).netloc == domain
            and not any(
                link.endswith(ext)
                for ext in (".pdf", ".png", ".jpg", ".zip", ".css", ".js")
            )
        )
    )

    logger.info(
        "scraping_url_success",
        url=url,
        extracted_length=len(extracted_text),
        found_subpages=len(same_domain_links),
    )
    return extracted_text, same_domain_links


async def scrape_college_urls_to_file(
    urls: List[str], college_name: str, max_pages: int = 15
) -> str:
    """Scrape college root URLs and discover/crawl internal subpages automatically.

    Returns the file path of the combined scraped knowledge base.
    """
    output_dir = os.path.join("data", "scraped")
    os.makedirs(output_dir, exist_ok=True)

    safe_name = re.sub(r"[^\w\-]", "_", college_name.lower().strip())
    file_path = os.path.join(output_dir, f"{safe_name}_scraped.txt")

    visited_urls = set()
    to_visit = list(urls)
    all_content_parts = [
        f"Official College Knowledge Base for {college_name}\n"
        f"Initial Seed URLs: {', '.join(urls)}\n\n"
    ]

    scraped_count = 0
    while to_visit and scraped_count < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited_urls:
            continue

        visited_urls.add(current_url)
        try:
            text, discovered_links = await fetch_web_page_and_links(current_url)
            if text:
                scraped_count += 1
                header_text = (
                    f"=== WEB PAGE CONTENT FROM ({scraped_count}/{max_pages}): "
                    f"{current_url} ===\n{text}\n\n"
                )
                all_content_parts.append(header_text)
                for link in discovered_links:
                    if link not in visited_urls and link not in to_visit:
                        to_visit.append(link)
        except Exception as e:
            logger.error("scrape_url_failed", url=current_url, error=str(e))

    combined_text = "\n".join(all_content_parts)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(combined_text)

    logger.info(
        "college_scraping_completed",
        college_name=college_name,
        file_path=file_path,
        scraped_pages_count=scraped_count,
        total_length=len(combined_text),
    )
    return file_path
