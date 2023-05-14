import logging
import sys

logger = logging.Logger("runsk")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("::[%(levelname)s]: %(message)s"))
logger.addHandler(handler)

subprocess_logger = logging.Logger("runsk subprocess")
subprocess_handler = logging.StreamHandler(sys.stdout)
subprocess_handler.setFormatter(logging.Formatter("[%(subprocess)s]: %(message)s"))
subprocess_handler.terminator = ''
subprocess_logger.addHandler(subprocess_handler)
