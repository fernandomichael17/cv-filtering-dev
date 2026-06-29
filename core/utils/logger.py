import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(debug: bool = False):
    """
    Configures logging for the application.
    Logs are output to the console and saved to 'logs/cv_filtering.log'.
    """
    # Ensure logs directory exists
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(log_dir, "cv_filtering.log")

    # Define log format
    log_format = "%(asctime)s - %(levelname)s - %(message)s"

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Silence noisy third-party loggers
    noisy_loggers = [
        "openai",
        "httpx",
        "httpcore",
        "python_multipart",
        "hpack",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
    ]
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Remove existing handlers to avoid duplicates
    while root_logger.handlers:
        root_logger.removeHandler(root_logger.handlers[0])

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    )
    root_logger.addHandler(console_handler)

    # File Handler (Rotating: 5MB per file, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    )
    root_logger.addHandler(file_handler)

    logging.info(f"Logging initialized. Mode: {'DEBUG' if debug else 'INFO'}")
