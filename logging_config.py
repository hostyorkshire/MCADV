#!/usr/bin/env python3
"""
Logging configuration for MCADV Adventure Bot and MeshCore
Provides file-based logging with rotation and multiple log levels
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logger(name: str, log_file: str, level=logging.INFO, console_output: bool = True, file_output: bool = True):
    """
    Set up a logger with both file and console handlers.

    Args:
        name: Logger name (e.g., 'adventure_bot', 'meshcore')
        log_file: Log file name (e.g., 'adventure_bot.log')
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        console_output: Enable console output (default: True)
        file_output: Enable file output (default: True)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers
    if logger.handlers:
        return logger

    # Create formatter
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(name)s [%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler with rotation 
    # For Pi: smaller files (5MB), fewer backups (3) to save SD card space
    if file_output:
        log_path = LOGS_DIR / log_file
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, 
            maxBytes=5 * 1024 * 1024,  # 5 MB (reduced for Pi)
            backupCount=3,  # Keep 3 backups (reduced for Pi)
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def setup_error_logger(name: str, error_log_file: str):
    """
    Set up a separate error logger for ERROR and CRITICAL messages only.

    Args:
        name: Logger name (e.g., 'adventure_bot_errors')
        error_log_file: Error log file name (e.g., 'adventure_bot_error.log')

    Returns:
        Configured error logger instance
    """
    error_logger = logging.getLogger(name)
    error_logger.setLevel(logging.ERROR)

    # Avoid adding duplicate handlers
    if error_logger.handlers:
        return error_logger

    # Create formatter with detailed error information
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(name)s [%(levelname)s]: %(message)s\n"
        "Location: %(pathname)s:%(lineno)d in %(funcName)s\n",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Error file handler with rotation
    # For Pi: smaller files (5MB), fewer backups (3) to save SD card space
    error_log_path = LOGS_DIR / error_log_file
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_path, 
        maxBytes=5 * 1024 * 1024,  # 5 MB (reduced for Pi)
        backupCount=3,  # Keep 3 backups (reduced for Pi)
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_logger.addHandler(error_handler)

    return error_logger


def get_adventure_bot_logger(debug: bool = False):
    """
    Get configured logger for the Adventure Bot.

    Args:
        debug: Enable DEBUG level logging (default: False)

    Returns:
        Tuple of (main_logger, error_logger)
    """
    level = logging.DEBUG if debug else logging.INFO

    main_logger = setup_logger(
        name="adventure_bot",
        log_file="adventure_bot.log",
        level=level,
        console_output=debug,  # Only show console output in debug mode
        file_output=True,
    )

    error_logger = setup_error_logger(name="adventure_bot_errors", error_log_file="adventure_bot_error.log")

    return main_logger, error_logger


def get_meshcore_logger(debug: bool = False):
    """
    Get configured logger for MeshCore.

    Args:
        debug: Enable DEBUG level logging (default: False)

    Returns:
        Tuple of (main_logger, error_logger)
    """
    level = logging.DEBUG if debug else logging.INFO

    main_logger = setup_logger(
        name="meshcore",
        log_file="meshcore.log",
        level=level,
        console_output=debug,  # Only show console output in debug mode
        file_output=True,
    )

    error_logger = setup_error_logger(name="meshcore_errors", error_log_file="meshcore_error.log")

    return main_logger, error_logger


def log_startup_info(logger, app_name: str, version: str = "1.0.0"):
    """Log startup information."""
    logger.info("=" * 70)
    logger.info(f"{app_name} Starting")
    logger.info(f"Version: {version}")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Logs directory: {LOGS_DIR.absolute()}")
    logger.info("=" * 70)


def log_exception(logger, error_logger, exception: Exception, context: str = ""):
    """
    Log an exception to both main and error logs.

    Args:
        logger: Main logger
        error_logger: Error logger
        exception: Exception to log
        context: Additional context about where the error occurred
    """
    msg = f"{context}: {type(exception).__name__}: {str(exception)}" if context else str(exception)
    logger.error(msg, exc_info=True)
    error_logger.error(msg, exc_info=True)
