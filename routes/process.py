"""
routes/process.py - Endpoints for processing suppliers.
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
      """Process one supplier from JSON body."""
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
      """Upload a CSV file. Processing runs in background."""
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
                            detail=f"CSV is missing required columns: {missing}.",
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
    background_tasks.add_task(run_batch, suppliers, output_file="output/csv_results.csv")

    return {
              "message": f"Processing {len(suppliers)} suppliers in the background.",
              "count": len(suppliers),
              "download_when_ready": "/api/export/csv",
    }


@router.post("/sheets")
async def process_from_sheets(background_tasks: BackgroundTasks):
      """Read pending suppliers from Google Sheets and process them."""
      try:
                suppliers = read_pending_suppliers()
except Exception as e:
        raise HTTPException(
                      status_code=500,
                      detail=f"Could not read from Google Sheets: {e}.",
        )

    if not suppliers:
              return {"message": "No pending suppliers found in the sheet.", "count": 0}

    logger.info(f"Sheets: {len(suppliers)} pending suppliers found")
    background_tasks.add_task(run_batch, suppliers, write_to_sheets=True)

    return {
              "message": f"Processing {len(suppliers)} suppliers from Google Sheets.",
              "count": len(suppliers),
    }
