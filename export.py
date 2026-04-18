"""
routes/export.py — Download processed results.
"""

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/csv")
def download_csv():
    """Download the most recently processed results as a CSV file."""
    output_path = "output/csv_results.csv"
    if not os.path.exists(output_path):
        raise HTTPException(
            status_code=404,
            detail="No results file found yet. Run a processing job first.",
        )
    return FileResponse(
        path=output_path,
        media_type="text/csv",
        filename="scie_results.csv",
    )
