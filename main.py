"""
Main entry point for the Medical Triage API.
Run from project root: python main.py
"""

import uvicorn
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import app_config
from backend.utils.logger import get_logger

logger = get_logger("main")

if __name__ == "__main__":
    logger.info("Starting Medical Triage API Server...")
    logger.info(f"Host: {app_config.api_host}:{app_config.api_port}")
    logger.info("Swagger docs: http://localhost:8000/docs")

    uvicorn.run(
        "backend.api.server:app",
        host=app_config.api_host,
        port=app_config.api_port,
        reload=app_config.debug,
        log_level=app_config.log_level.lower(),
    )
