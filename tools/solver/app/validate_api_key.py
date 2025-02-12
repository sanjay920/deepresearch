import os
import sys
import logging
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_openai_key():
    if "OPENAI_API_KEY" not in os.environ:
        logger.error("OPENAI_API_KEY environment variable must be set")
        sys.exit(1)

    try:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        # A quick call to confirm that the API key is valid
        client.models.list()
        logger.info("OpenAI API key validated successfully")
    except Exception as e:
        logger.error(f"Failed to validate OpenAI API key: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    validate_openai_key()
