import os
import sys
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Updated imports for Vertex AI
from google import genai
from google.genai import types
from google.api_core.exceptions import (
    GoogleAPIError,
    ResourceExhausted,
    InvalidArgument,
)
from google.oauth2 import service_account

# -------------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# -------------------------------------------------------------------------
# FastAPI App Setup
# -------------------------------------------------------------------------
app = FastAPI(
    title="Gemini Webpage Researcher Microservice",
    description=(
        "A microservice that accepts a URL and a query, then uses the Gemini model "
        "via Vertex AI to extract or answer questions based on the webpage content. "
        "The input query and the scraped webpage content are used to generate a markdown-formatted answer."
    ),
    version="1.0.0",
)

# -------------------------------------------------------------------------
# Vertex AI Client Setup
# -------------------------------------------------------------------------
try:
    # Path to service account JSON file
    SERVICE_ACCOUNT_FILE = os.environ.get(
        "SERVICE_ACCOUNT_FILE", "service-account.json"
    )
    PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
    LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logger.error(f"Service account file {SERVICE_ACCOUNT_FILE} not found")
        sys.exit(1)

    if not PROJECT_ID:
        logger.error("GCP_PROJECT_ID environment variable must be set")
        sys.exit(1)

    # Set up authentication scopes
    scopes = [
        "https://www.googleapis.com/auth/generative-language",
        "https://www.googleapis.com/auth/cloud-platform",
    ]

    # Create credentials from service account file
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=scopes,
    )

    # Initialize Vertex AI client
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=LOCATION,
        credentials=credentials,
    )

    # Define the model to use
    GEMINI_MODEL = "gemini-2.0-pro-exp-02-05"

    # Set conservative token limits
    # Gemini 1.5 Pro has a 2M token context window
    INPUT_TOKEN_LIMIT = 1900000  # Conservative estimate for 2M context window
    OUTPUT_TOKEN_LIMIT = 8192

    logger.info(f"Initialized Vertex AI client for project {PROJECT_ID} in {LOCATION}")
    logger.info(
        f"Using model {GEMINI_MODEL} with input token limit: {INPUT_TOKEN_LIMIT}, output token limit: {OUTPUT_TOKEN_LIMIT}"
    )

except Exception as e:
    logger.error(f"Failed to initialize Vertex AI client: {str(e)}")
    sys.exit(1)


# -------------------------------------------------------------------------
# Request Model
# -------------------------------------------------------------------------
class ResearchRequest(BaseModel):
    query: str
    url: str


# -------------------------------------------------------------------------
# Scraping Function
# -------------------------------------------------------------------------
def execute_scrape_tool(url: str, use_cache: bool = True) -> str:
    """
    Execute the scrape_url tool by calling the external scraping service
    """
    try:
        params = {
            "url": url,
            "force_fetch": not use_cache,
        }
        # Add error handling and better logging
        scraper_url = "http://host.docker.internal:8084/scrape"
        response = requests.get(scraper_url, params=params)
        response.raise_for_status()

        scraped_data = response.json()
        content = scraped_data["markdown"]

        # Check token count
        token_count = count_tokens(content)
        logger.info(f"Content from {url} has approximately {token_count} tokens")

        # Limit content size to avoid Gemini API limits
        # Use 95% of the input token limit to leave room for the query and system instruction
        max_tokens = int(INPUT_TOKEN_LIMIT * 0.95)

        if token_count > max_tokens:
            logger.warning(
                f"Content from {url} is very large ({token_count} tokens, limit is {max_tokens}). Truncating."
            )

            # Since we don't have direct access to truncate by tokens,
            # we'll estimate based on the ratio of tokens to characters
            char_to_token_ratio = len(content) / token_count
            char_limit = int(max_tokens * char_to_token_ratio)

            content = (
                content[:char_limit] + "\n\n[Content truncated due to token limit]"
            )

            # Verify our truncation worked
            new_token_count = count_tokens(content)
            logger.info(f"After truncation: {new_token_count} tokens")

        return content
    except requests.RequestException as e:
        logger.error(f"Error calling scraping service for URL {url}: {str(e)}")
        # Return a more structured error response
        raise HTTPException(
            status_code=502,
            detail={
                "error": "upstream_error",
                "message": f"Error scraping URL: {str(e)}",
                "url": url,
            },
        )


# -------------------------------------------------------------------------
# Gemini API Call with Retry Logic
# -------------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((GoogleAPIError, ResourceExhausted)),
)
def generate_content_with_retry(
    prompt: str, structured_output: Optional[Dict[str, Any]] = None
):
    """Generate content with retry logic for handling server errors."""

    # Get current timestamp for system prompt
    timestamp = datetime.now().strftime("%B %d, %Y %I:%M:%S %p")

    # Enhanced generalized system instruction with additional guidance
    system_instruction = (
        f"You are a thorough webpage researcher. You are provided with the content of a webpage and a user query. "
        f"Analyze the webpage content to extract or answer the query comprehensively. If the information is missing, state that it is not available. "
        f"\nProvide a detailed response that includes:"
        f"\n- All relevant facts and information from the webpage that address the query"
        f"\n- Specific details such as names, dates, places, prices, specifications, statistics, or measurements when available"
        f"\n- Direct quotes from the source material when relevant (always in quotation marks)"
        f"\n- Context and background information that helps understand the answer"
        f"\n- Comparisons, categories, or relationships mentioned on the webpage"
        f"\n- Any notable achievements, milestones, or turning points relevant to the query"
        f"\n\nVery important: Include all relevant links from the webpage that relate to your answer. "
        f"For each link you mention, include both the link text and the full URL in markdown format: [link text](URL)."
        f"\n\nOrganize your response with:"
        f"\n- A clear introduction summarizing the key points"
        f"\n- Logical headings and subheadings that break down the information"
        f"\n- Bullet points or numbered lists for easy readability"
        f"\n- Tables for comparative data when appropriate"
        f"\n- A conclusion or summary section when the topic warrants it"
        f"\n\nTailor your response based on content type:"
        f"\n- For people: Include biographical details, timeline of key events, relationships, achievements, and formative experiences"
        f"\n- For products/shopping: Include prices, features, specifications, availability, reviews, and alternatives"
        f"\n- For news: Include key events, dates, people involved, causes, effects, and background context"
        f"\n- For sports: Include scores, statistics, player information, game/match details, and historical context"
        f"\n- For technical content: Include steps, requirements, compatibility information, and code examples if present"
        f"\n- For historical topics: Include chronology, key figures, causes and effects, and significance"
        f"\n\nBe very verbose and thorough as your report will be used by downstream tools to extract information. "
        f"Return your answer in clear markdown format with any references to the source page as needed. "
        f"The current date and time is {timestamp}."
    )

    try:
        # For Vertex AI, we use the models.generate_content method directly
        # Set up generation config
        generation_config = types.GenerateContentConfig(
            temperature=0.2,
            top_p=1,
            top_k=32,
            max_output_tokens=8192,  # Conservative default
            system_instruction=system_instruction,
        )

        # Handle structured output if provided
        if structured_output:
            generation_config.response_mime_type = "application/json"
            generation_config.response_schema = structured_output

        # Call Vertex AI to generate content
        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=[prompt],
            config=generation_config,
        )

        return response

    except ResourceExhausted as e:
        logger.error(f"Vertex AI quota exceeded: {str(e)}")
        raise
    except InvalidArgument as e:
        logger.error(f"Invalid argument to Vertex AI: {str(e)}")
        # If the error is due to token limit, try to reduce the content
        if "exceeds the maximum token limit" in str(e):
            logger.info("Token limit exceeded, attempting to reduce content size")
            # Reduce by 20%
            new_char_limit = int(len(prompt) * 0.8)
            truncated_prompt = (
                prompt[:new_char_limit] + "\n\n[Content truncated due to token limit]"
            )

            # Try again with truncated content
            return generate_content_with_retry(truncated_prompt, structured_output)
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling Vertex AI: {str(e)}")
        raise


# -------------------------------------------------------------------------
# /research Endpoint
# -------------------------------------------------------------------------
@app.post("/research", summary="Research a webpage to answer a query")
def research_webpage(request: ResearchRequest):
    """
    Given a URL and a query, this endpoint uses the external scraping service to get webpage content
    and then asks Gemini via Vertex AI to answer or extract information based on that content.

    The response is a markdown-formatted answer.
    """
    correlation_id = str(uuid.uuid4())
    logger.info(
        f"Received research request (correlation_id: {correlation_id}) for URL: {request.url}"
    )

    # Step 1: Get webpage content using the scraping service
    scraped_content = execute_scrape_tool(request.url)
    if not scraped_content:
        raise HTTPException(
            status_code=400, detail="No content could be scraped from the provided URL."
        )

    # Step 2: Prepare prompt for Gemini
    prompt = f"Query: {request.query}\n\nWebpage URL: {request.url}\n\nWebpage Content:\n\n{scraped_content}"

    # Step 3: Call the Gemini model via Vertex AI
    try:
        response = generate_content_with_retry(prompt)
        answer_text = response.text
        logger.info(
            f"Vertex AI Gemini answered the research query (correlation_id: {correlation_id})"
        )
    except Exception as e:
        logger.error(f"Error in processing Vertex AI request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error processing the research query: {str(e)}"
        )

    # Step 4: Return answer
    return {
        "answer": answer_text,
        "correlation_id": correlation_id,
        "url": request.url,
        "query": request.query,
    }


# -------------------------------------------------------------------------
# /research_structured Endpoint for JSON output
# -------------------------------------------------------------------------
@app.post(
    "/research_structured", summary="Research a webpage and return structured data"
)
def research_webpage_structured(request: ResearchRequest):
    """
    Similar to /research but returns a structured JSON response based on the query.
    This is useful for extracting specific data points from webpages.
    """
    correlation_id = str(uuid.uuid4())
    logger.info(
        f"Received structured research request (correlation_id: {correlation_id}) for URL: {request.url}"
    )

    # Step 1: Get webpage content using the scraping service
    scraped_content = execute_scrape_tool(request.url)
    if not scraped_content:
        raise HTTPException(
            status_code=400, detail="No content could be scraped from the provided URL."
        )

    # Step 2: Prepare prompt for Gemini
    prompt = f"Extract structured data from this webpage to answer the query: {request.query}\n\nWebpage URL: {request.url}\n\nWebpage Content:\n\n{scraped_content}"

    # Define a generic schema for structured output
    # This is a simple example - in production, you might want to dynamically generate schemas based on the query
    structured_output = {
        "type": "OBJECT",
        "properties": {
            "answer": {"type": "STRING", "description": "The answer to the query"},
            "extracted_data": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
                "description": "Any data points extracted from the webpage",
            },
            "confidence": {
                "type": "NUMBER",
                "description": "Confidence level in the answer (0-1)",
            },
        },
    }

    # Step 3: Call the Gemini model with structured output
    try:
        response = generate_content_with_retry(prompt, structured_output)
        structured_answer = response.text
        # Parse the JSON string into a Python dictionary
        import json

        parsed_answer = json.loads(structured_answer)
        logger.info(
            f"Vertex AI Gemini provided structured answer (correlation_id: {correlation_id})"
        )
    except Exception as e:
        logger.error(
            f"Error in processing structured Vertex AI request: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error processing the structured research query: {str(e)}",
        )

    # Step 4: Return structured answer
    return {
        "structured_data": parsed_answer,
        "correlation_id": correlation_id,
        "url": request.url,
        "query": request.query,
    }


# -------------------------------------------------------------------------
# Token Counting Function
# -------------------------------------------------------------------------
def count_tokens(text: str) -> int:
    """
    Count the number of tokens in the text using the Gemini tokenizer.
    This is an estimate as we don't have direct access to the tokenizer.
    A conservative estimate is 4 characters per token.
    """
    try:
        # Try to use the actual tokenizer if available
        response = client.models.count_tokens(model="gemini-1.5-pro", contents=[text])
        return response.total_tokens
    except Exception as e:
        # Fall back to character-based estimation if tokenizer is not available
        logger.warning(
            f"Could not use tokenizer, falling back to character estimation: {str(e)}"
        )
        # Conservative estimate: 4 characters per token
        return len(text) // 4


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)
