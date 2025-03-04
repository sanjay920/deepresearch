import os
import sys
import logging
from google import genai
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_vertex_ai_credentials():
    """Validate Vertex AI credentials and connection."""

    # Check for required environment variables
    service_account_file = os.environ.get("SERVICE_ACCOUNT_FILE")
    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GCP_LOCATION", "us-central1")

    if not service_account_file:
        logger.error("SERVICE_ACCOUNT_FILE environment variable must be set")
        sys.exit(1)

    if not os.path.exists(service_account_file):
        logger.error(f"Service account file {service_account_file} not found")
        sys.exit(1)

    if not project_id:
        logger.error("GCP_PROJECT_ID environment variable must be set")
        sys.exit(1)

    try:
        # Set up authentication scopes
        scopes = [
            "https://www.googleapis.com/auth/generative-language",
            "https://www.googleapis.com/auth/cloud-platform",
        ]

        # Create credentials from service account file
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=scopes,
        )

        # Initialize Vertex AI client
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            credentials=credentials,
        )

        # Test the client by listing models
        logger.info(f"Testing Vertex AI connection for project {project_id}")
        models = client.models.list()
        gemini_models_found = False

        for model in models:
            if "gemini" in model.name.lower():
                logger.info(f"Found Gemini model: {model.name}")
                gemini_models_found = True

        if not gemini_models_found:
            logger.warning("No Gemini models found, but Vertex AI connection is valid")

        logger.info(
            f"Vertex AI credentials validated successfully for project {project_id}"
        )

    except Exception as e:
        logger.error(f"Failed to validate Vertex AI credentials: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    validate_vertex_ai_credentials()
