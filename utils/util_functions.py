import logging
import logging.config

from utils.constants import LOG_CONFIG_FILE

def setup_logging():
    """
    set up logging func
    """
    logging.config.fileConfig(LOG_CONFIG_FILE)

def setup_defaults():
    "setup default functions"
    setup_logging()

def get_logger(name=None):
    """
    Get a logger instance.
    
    Args:
        name (str): Logger name. If None, returns the 'app' logger.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    print("inside logger %s", name)
    if name is None:
        return logging.getLogger('root')
    return logging.getLogger(name)