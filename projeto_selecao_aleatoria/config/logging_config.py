# logging_config.py
import logging
import os
from logging.handlers import RotatingFileHandler

def configure_logging():
    """
    Configure comprehensive logging for the RPA Docker processing.
    
    This configuration:
    - Logs to both console and file
    - Uses rotating file handler to manage log file size
    - Provides detailed logging format
    - Creates log directory if it doesn't exist
    """
    # Ensure logs directory exists
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create a rotating file handler
    log_file = os.path.join(log_dir, 'rpa_docker_processing.log')
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5  # Keep 5 backup logs
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Add file handler to loggers
    loggers = [
        logging.getLogger('RPADockerProcessor'),
        logging.getLogger('django'),
        logging.getLogger(__name__)
    ]
    
    for logger in loggers:
        logger.addHandler(file_handler)

# Call this function early in your application startup
configure_logging()