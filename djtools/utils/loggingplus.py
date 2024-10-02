import logging
from functools import wraps, WRAPPER_ASSIGNMENTS

__all__ = ['prevent_logging_errors']


def prevent_logging_errors(log='django.request'):
    def receive_function(original_function):
        @wraps(original_function, assigned=WRAPPER_ASSIGNMENTS)
        def receive_function_args(*args, **kwargs):
            # raise logging level to CRITICAL
            logger = logging.getLogger(log)
            previous_logging_level = logger.getEffectiveLevel()
            logger.setLevel(logging.CRITICAL)

            # trigger original function that would throw warning
            original_function(*args, **kwargs)

            # lower logging level back to previous
            logger.setLevel(previous_logging_level)

        return receive_function_args
    return receive_function
