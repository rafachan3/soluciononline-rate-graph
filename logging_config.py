import logging
from logging.handlers import RotatingFileHandler
import os
import datetime
import glob

def setup_logging(log_dir="logs", max_logs=3):
    """Configure application logging with new file per run and limit on total logs."""
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate timestamp for unique log file
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = os.path.join(log_dir, f"app_{timestamp}.log")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )
    
    # Standard file handler (no rotation needed since we're creating new files per run)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler for warnings and errors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only show warnings and errors in console
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Suppress logs from third-party libraries
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Clean up old log files, keeping only the most recent ones
    _cleanup_old_logs(log_dir, max_logs)
    
    logging.info(f"Logging initialized: writing to {log_filename}")
    return root_logger

def _cleanup_old_logs(log_dir, max_logs):
    """Delete older log files, keeping only the most recent ones."""
    log_files = glob.glob(os.path.join(log_dir, "app_*.log"))
    
    # Sort by modification time (newest first)
    log_files.sort(key=os.path.getmtime, reverse=True)
    
    # Remove all but the most recent max_logs files
    for old_file in log_files[max_logs:]:
        try:
            os.remove(old_file)
        except Exception as e:
            # Just log failures but don't stop the program
            print(f"Failed to remove old log file {old_file}: {e}")