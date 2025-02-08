import logging
from logging.handlers import RotatingFileHandler


# Logging Levels:

# DEBUG: detailed information, typically of interest only when diagnosing problems.
# INFO: confirmation that things are working as expected.
# WARNING: an indication that something unexpected happened, or indicative of some problem in the near future.
# ERROR: due to a more serious problem, the software has not been able to preform some function.
# CRITICAL: a serous error indicating that the program itself may be unable to continue running

# default logging level is warning (only warnings and above are printed)

def configure_logger(
        # todo: maybe use **kwargs instead of explicitly mention variables.
        stream_level=logging.CRITICAL,
        logging_level=logging.INFO,
        log_to_file=True,
        print_logging=False,
        log_output_path=None,
        cyclic_log_files=False,
        cyclic_max_bytes=2000,
        cyclic_backup_count=10,
        logger_name=None,
        propagate=False,
        message_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
):
    """
    basic initialization of logger.
    :param propagate:
    :param stream_level:
    :param message_format:
    :param logging_level:
    :param log_to_file:
    :param print_logging:
    :param log_output_path:
    :param cyclic_log_files:
    :param cyclic_max_bytes:
    :param cyclic_backup_count:
    :param logger_name:
    :return: Logging.logger object
    """

    if log_output_path is None:
        log_output_path = 'Main.log'

    logging.basicConfig(format=message_format, datefmt='%d-%b-%y %H:%M:%S')

    # if no logger was provided use root logger object and formatter
    if logger_name is None:
        logger = logging.getLogger()

    # if a logger was provided we will rewrite its handlers
    else:
        logger = logging.getLogger(logger_name)

    formatter = logging.Formatter(message_format)

    # remove all default handlers (enables print only)
    for handler in logger.handlers:
        logger.removeHandler(handler)

    # add file output
    if log_to_file:
        if cyclic_log_files:
            fh = RotatingFileHandler(
                log_output_path,
                maxBytes=cyclic_max_bytes, backupCount=cyclic_backup_count
                )

        else:
            fh = logging.FileHandler(log_output_path)

        fh.setFormatter(formatter)
        logger.addHandler(fh)

    # add print output
    if print_logging:
        terminal_handle = logging.StreamHandler()
        terminal_handle.setLevel(stream_level)
        terminal_handle.setFormatter(formatter)
        logger.addHandler(terminal_handle)

    logger.setLevel(logging_level)

    logger.propagate = propagate

    return logger
