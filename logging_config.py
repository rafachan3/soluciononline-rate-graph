import logging
from logging.handlers import RotatingFileHandler
import os
import datetime
import glob

def setup_logging(log_dir="logs", max_logs=3):
    """
    Configure application logging with a comprehensive setup.
    
    This function sets up a robust logging system with the following features:
    - Creates a new log file per run with timestamp in filename
    - Configures console output for warnings and errors (for immediate visibility)
    - Configures detailed file logging for all messages (for troubleshooting)
    - Automatically cleans up old log files to prevent disk space issues
    - Suppresses excessive logging from third-party libraries
    
    Args:
        log_dir (str): Directory where log files should be stored
        max_logs (int): Maximum number of log files to keep before cleaning up old ones
        
    Returns:
        logging.Logger: Configured root logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate timestamp for unique log file
    # This ensures each run has its own log file for easier troubleshooting
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = os.path.join(log_dir, f"app_{timestamp}.log")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Create formatters - different formats for file vs console
    # File logs need detailed information for troubleshooting
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )
    
    # Standard file handler (no rotation needed since we're creating new files per run)
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG) # Log everything to file
    file_handler.setFormatter(file_formatter)
    
    # Console handler for warnings and errors only
    # This prevents console flooding while still showing important messages
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only show warnings and errors in console
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Suppress logs from third-party libraries
    # These libraries tend to be very verbose at debug level
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Clean up old log files, keeping only the most recent ones
    # This prevents accumulating too many logs over time
    _cleanup_old_logs(log_dir, max_logs)
    
    logging.info(f"Logging initialized: writing to {log_filename}")
    return root_logger

def _cleanup_old_logs(log_dir, max_logs):
    """
    Delete older log files, keeping only the most recent ones.
    
    This helper function prevents disk space issues by automatically
    removing older log files when a new log session starts. It ensures
    that only the most recent log files (based on modification time)
    are kept, up to the specified maximum.
    
    Args:
        log_dir (str): Directory containing log files
        max_logs (int): Maximum number of log files to keep
    """
    log_files = glob.glob(os.path.join(log_dir, "app_*.log"))
    
    # Sort by modification time (newest first)
    log_files.sort(key=os.path.getmtime, reverse=True)
    
    # Remove all but the most recent max_logs files
    for old_file in log_files[max_logs:]:
        try:
            os.remove(old_file)
        except Exception as e:
            # Just log failures but don't stop the program
            # This is non-critical functionality
            print(f"Failed to remove old log file {old_file}: {e}")