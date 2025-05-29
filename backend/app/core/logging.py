import logging
import sys
from pathlib import Path
from app.core.config import settings

# Use standard logging for testing
logger = logging.getLogger(__name__)

def setup_logging():
    """Simple logging setup for testing."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

# Configure logging when imported
setup_logging()
