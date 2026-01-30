import traceback
import logging
from typing import Union

import os


class DebugFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        request_details = ("Response headers:" in message) or (
            "Request headers:" in message
        )
        debug_message = record.levelno == logging.DEBUG
        return request_details or debug_message


class InfoFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        request_details = ("Response headers:" in message) or (
            "Request headers:" in message
        )
        return not request_details


logger: Union[None, logging.Logger] = None
# Create a logger
logger = logging.getLogger()
logger.setLevel(
    logging.DEBUG
)  # Set the logger level to the lowest level to capture all events

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.addFilter(InfoFilter())

# Determine the correct log file paths based on current working directory
log_dir = (
    ""
    if os.getcwd().endswith("server") or os.path.basename(os.getcwd()) == "server"
    else "server/"
)
if len(log_dir) > 0:
    os.makedirs(log_dir, exist_ok=True)

# Create a handler for writing INFO and above to applog.log
info_handler = logging.FileHandler(f"{log_dir}applog.log")
info_handler.setLevel(logging.INFO)  # Set this handler's level to INFO

# Add the filter to the debug handler
info_handler.addFilter(InfoFilter())

# Create a handler for writing DEBUG to applog_debug.log
debug_handler = logging.FileHandler(f"{log_dir}applog_debug.log")
debug_handler.setLevel(logging.DEBUG)  # Set this handler's level to DEBUG

# Add the filter to the debug handler
debug_handler.addFilter(DebugFilter())

# You can set different formats for the handlers if needed
formatter = logging.Formatter(
    fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# Apply the formatter to both handlers
info_handler.setFormatter(formatter)
debug_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(info_handler)
logger.addHandler(debug_handler)
logger.addHandler(console_handler)


def log_msg(msg: Union[str, Exception]) -> None:
    if logger is not None:
        if type(msg) == str:
            logger.info(msg)
        else:
            logger.exception(msg, extra={"stack": True})
    else:
        if type(msg) == str:
            print(msg)
        else:
            print(f"Exception occurred: {msg}\n{traceback.format_exc()}")
