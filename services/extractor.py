"""
services/extractor.py - AI-powered contact information extraction.

Uses Google Gemini (primary, free) or Anthropic Claude (fallback, paid)
to extract structured contact information from crawled web page text.
"""

import json
import re
from typing import List, Dict, Optional
from loguru import logger

from config import get_settings
from schemas.supplier import SupplierInput, SupplierContact, ContactPerson

settings = get_settings()

EXTRACTION_PROMPT_TEMPLATE = """You are a supplier contact intelligence extractor.
Analyze the following web page content from supplier "{supplier_name}" ({country}) and extract ALL contact information.

Pages crawled:
{pages_text}

Extract and return a JSON object with this exact structure:
{{
  "website": "main website URL",
    "general_email": "general contact email or null",
      "general_phone": "main phone number or null",
        "headquarters_address": "full address or null",
          "contacts": [
              {{
                    "name": "full name",
                          "title": "job title",
                                "email": "email address or null",
                                      "phone": "direct phone or null",
                                            "linkedin": "LinkedIn URL or null",
                                                  "department": "department or null",
                                                        "notes": "any additional relevant notes"
    }}
      ],
        "confidence_score": 0.0,
          "notes": "any additional relevant notes"
}}

Rules:
- Extract ALL named individuals found (sales, procurement, management, etc.)
- confidence_score: 0.0-1.0 based on quality/quantity of data found
- Return ONLY valid JSON, no markdown, no explanation
- If no contacts found, return empty contacts array
"""


async def extract_contacts_with_ai(
      supplier: SupplierInput,
      pages: List[Dict[str, str]],
      website_url: str,
) -> SupplierContact:
      """
          Use AI to extract contact information from crawled pages.
              Tries Gemini first (free), falls back to Claude if configured.
                  """
      # Prepare page text for the prompt
      pages_text = "\n\n---\n\n".join(
          f"URL: {p['url']}\n\n{p['text']}" for p in pages
      )

    prompt = EXTRACTION_PROMPT_TEMPLATE.format(
              supplier_name=supplier.supplier_name,
              country=supplier.country or "Unknown",
              pages_text=pages_text[:15000],  # cap total prompt size
    )

    # Try Gemini first
    if settings.gemini_api_key:
              try:
                            result = await _extract_with_gemini(prompt)
                            return _parse_ai_response(result, supplier, website_url)
except Exception as e:
            logger.warning(f"Gemini extraction failed: {e}, trying fallback...")

    # Fall back to Anthropic Claude
    if settings.anthropic_api_key:
              try:
                            result = await _extract_with_claude(prompt)
                            return _parse_ai_response(result, supplier, website_url)
except Exception as e:
            logger.error(f"Claude extraction also failed: {e}")

    # No AI available - return empty result
    logger.error(f"No AI API keys configured for {supplier.supplier_name}")
    return SupplierContact(
              supplier_name=supplier.supplier_name,
              website=website_url,
              country=supplier.country,
              category=supplier.category,
              notes="AI extraction failed. Check API keys in .env file.",
    )


async def _extract_with_gemini(prompt: str) -> str:
      """Call Google Gemini API."""
      import httpx
      url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.gemini_api_key}"
      payload = {
          "contents": [{"parts": [{"text": prompt}]}],
          "generationConfig": {
              "temperature": 0.1,
              "maxOutputTokens": 4096,
          },
      }
      async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]


async def _extract_with_claude(prompt: str) -> str:
      """Call Anthropic Claude API."""
      import httpx
      headers = {
          "x-api-key": settings.anthropic_api_key,
          "anthropic-version": "2023-06-01",
          "content-type": 
