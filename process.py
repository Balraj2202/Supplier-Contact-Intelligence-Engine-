"""
routes/process.py — Endpoints for processing suppliers.

Endpoints:
  POST /api/process/single   — process one supplier from JSON body
  POST /api/process/csv      — process a CSV file upload
  POST /api/process/sheets   — process pending rows from Google Sheets
"""

import io
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from loguru import logger

from schemas.supplier import SupplierInput, ProcessingResult
from services.pipeline import run_single_supplier, run_batch
from integrations.sheets import read_pending_suppliers, write_results_to_sheet

router = APIRouter()


@router.post("/single", response_model=ProcessingResult)
async def process_single(supplier: SupplierInput):
    """
    Process one supplier. Send a JSON body with supplier details.
    
    Example body:
    {
        "supplier_name": "Acme Corp",
        "country": "Germany",
        "website_hint": "acmecorp.com",
        "category": "electronics"
    }
    """
    logger.info(f"Processing single supplier: {supplier.supplier_name}")
    try:
        result = await run_single_supplier(supplier)
        return result
    except Exception as e:
        logger.error(f"Error processing {supplier.supplier_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/csv")
async def process_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Upload a CSV file. Returns a job ID immediately; processing runs in background.
    
    CSV must have at minimum a 'supplier_name' column.
    See samples/sample-input.csv for the expected format.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv file")

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {e}")

    required_columns = ["supplier_name"]
    missing = [c for c in required_columns if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns: {missing}. "
                   f"See samples/sample-input.csv for the correct format.",
        )

    suppliers = []
    for _, row in df.iterrows():
        suppliers.append(
            SupplierInput(
                supplier_name=str(row.get("supplier_name", "")),
                country=str(row.get("country", "")),
                website_hint=str(row.get("website", "")),
                category=str(row.get("category", "")),
            )
        )

    logger.info(f"CSV upload: {len(suppliers)} suppliers queued for processing")

    # Run in background so the API responds immediately
    background_tasks.add_task(run_batch, suppliers, output_file="output/csv_results.csv")

    return {
        "message": f"Processing {len(suppliers)} suppliers in the background.",
        "count": len(suppliers),
        "download_when_ready": "/api/export/csv",
    }


@router.post("/sheets")
async def process_from_sheets(background_tasks: BackgroundTasks):
    """
    Read pending suppliers from Google Sheets and process them.
    Requires GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_FILE in your .env file.
    See docs/setup-guide.md for Google Sheets setup instructions.
    """
    try:
        suppliers = read_pending_suppliers()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read from Google Sheets: {e}. "
                   f"Check your GOOGLE_SHEET_ID and credentials. See docs/setup-guide.md.",
        )

    if not suppliers:
        return {"message": "No pending suppliers found in the sheet.", "count": 0}

    logger.info(f"Sheets: {len(suppliers)} pending suppliers found")
    background_tasks.add_task(run_batch, suppliers, write_to_sheets=True)

    return {
        "message": f"Processing {len(suppliers)} suppliers from Google Sheets.",
        "count": len(suppliers),
    }
