import os
import logging


class GlobalDimensionsFilter(logging.Filter):
    """
    Injects 5W1H (Who, Where, How, etc.) and standard Application Insights fields
    into every standard Python log emitted by this application.
    """

    def filter(self, record):
        if not hasattr(record, "custom_dimensions"):
            record.custom_dimensions = {}

        # Standard Application Insights mapped fields
        record.user_Id = "test-user-python"
        record.application_Version = "1.0.0"

        # Custom dimensions (5W1H Context)
        record.custom_dimensions.update(
            {
                "Environment": "Lab",
                "AppVersion": "1.0.0",
                "Where": os.environ.get("OTEL_SERVICE_NAME", "python-api"),
            }
        )
        return True


def setup_logger(name="app"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addFilter(GlobalDimensionsFilter())
    return logger


logger = setup_logger()
