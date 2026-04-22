"""
services/pipeline.py - Core processing pipeline for supplier contact extraction.

This module orchestrates:
  1. Website discovery (find the supplier's actual website)
    2. Web crawling (fetch relevant pages)
      3. AI extraction (use Gemini/Claude to extract structured contact data)
        4. Result saving (write to CSV or Google Sheets)
        """

import asyncio
import time
import httpx
from typing import List, Optional
from loguru import logger

from config import get_settings
from schemas.supplier import SupplierInput, ProcessingResult, SupplierContact, ContactPerson
from services.crawler import discover_website, fetch_pages
from services.extractor import extract_contacts_with_ai

settings = get_settings()


async def run_single_supplier(supplier: SupplierInput) -> ProcessingResult:
      """
          Full pipeline for a single supplier:
              1. Discover website URL
                  2. Crawl relevant pages
                      3. Extract contacts with AI
                          """
      logger.info(f"Starting pipeline for: {supplier.supplier_name}")

    try:
              # Step 1: Discover/validate website
              website_url = await discover_website(supplier)
              if not website_url:
                            return ProcessingResult(
                                              supplier_name=supplier.supplier_name,
                                              status="failed",
                                              error="Could not find a website for this supplier.",
                            )

              # Step 2: Crawl pages
              pages = await fetch_pages(website_url, max_pages=settings.max_pages_per_supplier)
              if not pages:
                            return ProcessingResult(
                                              supplier_name=supplier.supplier_name,
                                              status="failed",
                                              error=f"Could not fetch any pages from {website_url}.",
                            )

              # Step 3: Extract contacts via AI
              contact_data = await extract_contacts_with_ai(supplier, pages, website_url)

        return ProcessingResult(
                      supplier_name=supplier.supplier_name,
                      status="success" if contact_data.contacts else "partial",
                      data=contact_data,
        )

except Exception as e:
        logger.error(f"Pipeline failed for {supplier.supplier_name}: {e}")
        return ProcessingResult(
                      supplier_name=supplier.supplier_name,
                      status="failed",
                      error=str(e),
        )


async def run_batch(
      suppliers: List[SupplierInput],
      output_file: Optional[str] = None,
      write_to_sheets: bool = False,
) -> List[ProcessingResult]:
      """
          Process a list of suppliers with rate limiting.
              Optionally saves results to a CSV or Google Sheets.
                  """
      results = []
      batch_size = settings.batch_size
      delay = settings.crawl_delay_seconds

    logger.info(f"Processing batch of {len(suppliers)} suppliers (batch_size={batch_size})")

    for i, supplier in enumerate(suppliers):
              logger.info(f"[{i+1}/{len(suppliers)}] Processing: {supplier.supplier_name}")
              result = await run_single_supplier(supplier)
              results.append(result)

        # Respect crawl delay between requests
              if i < len(suppliers) - 1:
                            await asyncio.sleep(delay)

          # Save results
          if output_file:
                    _save_to_csv(results, output_file)

    if write_to_sheets:
              from integrations.sheets import write_results_to_sheet
              write_results_to_sheet(results)

    logger.info(f"Batch complete: {len(results)} processed")
    return results


def _save_to_csv(results: List[ProcessingResult], output_file: str):
      """Save processing results to a CSV file."""
      import csv
      import os

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    rows = []
    for r in results:
              if r.data:
                            for contact in (r.data.contacts or [{}]):
                                              row = {
                                                                    "supplier_name": r.data.supplier_name,
                                                                    "website": r.data.website or "",
                                                                    "country": r.data.country or "",
                                                                    "category": r.data.category or "",
                                                                    "general_email": r.data.general_email or "",
                                                                    "general_phone": r.data.general_phone or "",
                                                                    "headquarters_address": r.data.headquarters_address or "",
                                                                    "contact_name": contact.name if isinstance(contact, ContactPerson) else "",
                                                                    "contact_title": contact.title if isinstance(contact, ContactPerson) else "",
                                                                    "contact_email": contact.email if isinstance(contact, ContactPerson) else "",
                                                                    "contact_phone": contact.phone if isinstance(contact, ContactPerson) else "",
                                                                    "contact_linkedin": contact.linkedin if isinstance(contact, ContactPerson) else "",
                                                                    "confidence_score": r.data.confidence_score or "",
                                                                    "status": r.status,
                                                                    "error": r.error or "",
                                              }
                                              rows.append(row)
              else:
                            rows.append({
                                              "supplier_name": r.supplier_name,
                                              "status": r.status,
                                              "error": r.error or "",
                            })

          if not rows:
                    logger.warning("No results to save to CSV")
                    return

    with open(output_file, "w", newline="", encoding="utf-8") as f:
              writer = csv.DictWriter(f, fieldnames=rows[0].keys())
              writer.writeheader()
              writer.writerows(rows)

    logger.info(f"Results saved to {output_file}")
