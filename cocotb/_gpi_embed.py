import logging


def _filter_from_c(logger_name, level):
    return logging.getLogger(logger_name).isEnabledFor(level)


def _log_from_c(logger_name, level, filename, lineno, msg, function_name):
    """Log from the C world, allowing to insert C stack information."""
    logger = logging.getLogger(logger_name)
    if logger.isEnabledFor(level):
        record = logger.makeRecord(
            logger.name,
            level,
            filename,
            lineno,
            msg,
            None,
            None,
            function_name
        )
        logger.handle(record)
