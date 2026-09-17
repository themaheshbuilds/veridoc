import logging
import sys

def setup_logging():
    """Configure structured logging for VERIDOC AI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Suppress overly chatty loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)

logger = logging.getLogger("veridoc")
