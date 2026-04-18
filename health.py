"""
routes/health.py — Simple health check endpoint.
Visit http://localhost:8000/health to confirm the server is running.
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "SCIE Backend",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }
