"""
schemas/supplier.py - Pydantic models for supplier data.
"""

from typing import Optional, List
from pydantic import BaseModel, HttpUrl


class SupplierInput(BaseModel):
      """Input data for a supplier to be processed."""
      supplier_name: str
      country: Optional[str] = ""
      website_hint: Optional[str] = ""
      category: Optional[str] = ""


class ContactPerson(BaseModel):
      """A single contact person at a supplier."""
      name: Optional[str] = None
      title: Optional[str] = None
      email: Optional[str] = None
      phone: Optional[str] = None
      linkedin: Optional[str] = None
      department: Optional[str] = None


class SupplierContact(BaseModel):
      """Structured contact information extracted from a supplier website."""
      supplier_name: str
      website: Optional[str] = None
      country: Optional[str] = None
      category: Optional[str] = None
      contacts: List[ContactPerson] = []
      general_email: Optional[str] = None
      general_phone: Optional[str] = None
      headquarters_address: Optional[str] = None
      confidence_score: Optional[float] = None
      source_urls: List[str] = []
      notes: Optional[str] = None


class ProcessingResult(BaseModel):
      """Result of processing a single supplier."""
      supplier_name: str
      status: str  # "success", "partial", "failed"
    data: Optional[SupplierContact] = None
    error: Optional[str] = None
