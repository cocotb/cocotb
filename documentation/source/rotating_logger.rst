.. _rotating-logger:

******************
Rotating Log Files
******************

The following is an example of how to support rotation of log files.
It will keep the newest 3 files which are at most 5 MiB in size.

See also :ref:`logging-reference-section`,
and the Python documentation for :class:`logging.handlers.RotatingFileHandler`.

.. code-block:: python3

    from logging.handlers import RotatingFileHandler

    root_logger = logging.getLogger()

    # undo the setup cocotb did
    for handler in root_logger.handlers:
        root_logger.remove_handler(handler)
        handler.close()

    # do whatever configuration you want instead
    file_handler = RotatingFileHandler(logfile, maxBytes=(5 * 1024 * 1024), backupCount=2)
    file_handler.setFormatter(cocotb.log.SimLogFormatter())
    root_logger.addHandler(file_handler)
