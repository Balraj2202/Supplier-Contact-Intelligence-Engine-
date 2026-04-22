"""
routes/logs.py - View recent processing logs.
"""

import os
from fastapi import APIRouter

router = APIRouter()


@router.get("")
def get_logs(lines: int = 100):
      """Return the last N lines from the log file."""
      log_path = "logs/scie.log"
      if not os.path.exists(log_path):
                return {"logs": [], "message": "No logs yet."}

      with open(log_path, "r") as f:
                all_lines = f.readlines()

      recent = all_lines[-lines:]
      return {"logs": [line.strip() for line in recent], "total_lines": len(all_lines)}
