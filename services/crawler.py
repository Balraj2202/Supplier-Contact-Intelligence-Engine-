"""
services/crawler.py - Web crawling and website discovery.

Handles:
  - Discovering a supplier's website via search or hint
    - Fetching and parsing relevant pages (contact, about, team)
    """

import re
import asyncio
from typing import List, Optional, Dict
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from schemas.supplier import SupplierInput

HEADERS = {
      "User-Agent": "Mozilla/5.0 (compatible; SCIE-Bot/1.0; +https://github.com/Balraj2202/Supplier-Contact-Intelligence-Engine-)",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.5",
}

# Pages most likely to contain contact information
PRIORITY_PATHS = [
      "/contact",
      "/contact-us",
      "/about",
      "/about-us",
      "/team",
      "/our-team",
      "/people",
      "/management",
      "/leadership",
      "/impressum",  # German legal contact page
]


async def discover_website(supplier: SupplierInput) -> Optional[str]:
      """
          Discover the supplier's website URL.
              Uses the website_hint if provided, otherwise falls back to search.
                  """
      hint = (supplier.website_hint or "").strip()

    if hint:
              # Normalize the hint to a full URL
              if not hint.startswith("http"):
                            hint = f"https://{hint}"

              # Verify the URL is accessible
              try:
                            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                                              resp = await client.head(hint, headers=HEADERS)
                                              if resp.status_code < 400:
                                                                    logger.info(f"Website hint verified: {resp.url}")
                                                                    return str(resp.url)
              except Exception as e:
                            logger.warning(f"Could not reach hint URL {hint}: {e}")

          # Fall back: try common patterns
          name_slug = re.sub(r"[^a-z0-9]", "", supplier.supplier_name.lower())
    candidates = [
              f"https://www.{name_slug}.com",
              f"https://{name_slug}.com",
              f"https://www.{name_slug}.de",
              f"https://www.{name_slug}.co.uk",
    ]

    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
              for url in candidates:
                            try:
                                              resp = await client.head(url, headers=HEADERS)
                                              if resp.status_code < 400:
                                                                    logger.info(f"Found website via candidate: {resp.url}")
                                                                    return str(resp.url)
                            except Exception:
                                              continue

                    logger.warning(f"Could not discover website for: {supplier.supplier_name}")
    return None


async def fetch_pages(base_url: str, max_pages: int = 5) -> List[Dict[str, str]]:
      """
          Fetch relevant pages from a supplier's website.
              Returns a list of dicts with 'url' and 'text' keys.
                  """
    pages = []
    visited = set()

    async with httpx.AsyncClient(
              timeout=15,
              follow_redirects=True,
              headers=HEADERS,
    ) as client:
              # Always fetch the homepage first
              homepage = await _fetch_page(client, base_url)
        if homepage:
                      pages.append(homepage)
                      visited.add(base_url)

        # Then fetch priority paths
        for path in PRIORITY_PATHS:
                      if len(pages) >= max_pages:
                                        break

                      url = urljoin(base_url, path)
                      if url in visited:
                                        continue

            page = await _fetch_page(client, url)
            if page:
                              pages.append(page)
                              visited.add(url)

    logger.info(f"Fetched {len(pages)} pages from {base_url}")
    return pages


async def _fetch_page(client: httpx.AsyncClient, url: str) -> Optional[Dict[str, str]]:
      """Fetch a single page and extract its text content."""
    try:
        resp = await client.get(url)
        if resp.status_code >= 400:
                      return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header"]):
                      tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)

        return {"url": str(resp.url), "text": text[:8000]}  # cap per page

except httpx.HTTPStatusError:
        return None
except Exception as e:
        logger.debug(f"Could not fetch {url}: {e}")
        return None
