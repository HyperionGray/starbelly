import logging
import sys


log_format = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
log_date_format = '%Y-%m-%d %H:%M:%S'
log_formatter = logging.Formatter(log_format, log_date_format)
log_handler = logging.StreamHandler(sys.stderr)
log_handler.setFormatter(log_formatter)
logger = logging.getLogger()
logger.addHandler(log_handler)
