"""
SCIE Backend — Main Entry Point
================================
Run this file to start the API server:
    python main.py
"""

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from loguru import logger

from routes.health import router as health_router
from routes.process import router as process_router
from routes.export import router as export_router
from routes.logs import router as logs_router

# Load environment variables from .env file
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logger.add("logs/scie.log", rotation="10 MB", retention="7 days", level=LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs when the app starts and stops."""
    logger.info("SCIE Backend starting up...")
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    yield
    logger.info("SCIE Backend shutting down.")


# Create the FastAPI app
app = FastAPI(
    title="Supplier Contact Intelligence Engine",
    description="Extract structured contact intelligence from supplier websites using AI.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow requests from the frontend (Next.js on localhost:3000 or your deployed URL)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",  # Replace with your actual Vercel URL
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all route groups
app.include_router(health_router, tags=["Health"])
app.include_router(process_router, prefix="/api/process", tags=["Processing"])
app.include_router(export_router, prefix="/api/export", tags=["Export"])
app.include_router(logs_router, prefix="/api/logs", tags=["Logs"])


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
