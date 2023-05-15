import logging
import sys


class NewlineStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # issue 35046: merged two stream.writes into one.
            final_message = msg if msg.endswith(self.terminator) else msg + self.terminator
            stream.write(final_message)
            self.flush()
        except RecursionError:  # See issue 36272
            raise
        except Exception:
            self.handleError(record)


logger = logging.Logger("runsk")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("::[%(levelname)s]: %(message)s"))
logger.addHandler(handler)

subprocess_logger = logging.Logger("runsk subprocess")
subprocess_handler = NewlineStreamHandler(sys.stdout)
subprocess_handler.setFormatter(logging.Formatter("[%(subprocess)s]: %(message)s"))
subprocess_logger.addHandler(subprocess_handler)

subprocess_logger_err = logging.Logger("runsk subprocess")
subprocess_handler_err = NewlineStreamHandler(sys.stderr)
subprocess_handler_err.setFormatter(logging.Formatter("[%(subprocess)s]: %(message)s"))
subprocess_logger_err.addHandler(subprocess_handler_err)
