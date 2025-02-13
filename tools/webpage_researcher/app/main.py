import os
import sys
import json
import logging
import uuid
from datetime import datetime

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from openai import OpenAI

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
    title="Webpage Researcher Microservice",
    description=(
        "A microservice that accepts a URL and a query, then uses the GPT‑4o model "
        "to extract or answer questions based on the webpage content. "
        "The input query and the scraped webpage content are used to generate a markdown-formatted answer."
    ),
    version="1.0.0",
)

# -------------------------------------------------------------------------
# OpenAI Client Setup (Using the latest OpenAI SDK)
# -------------------------------------------------------------------------
try:
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
except KeyError:
    logger.error("OPENAI_API_KEY environment variable must be set")
    sys.exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)


# -------------------------------------------------------------------------
# Request Model
# -------------------------------------------------------------------------
class ResearchRequest(BaseModel):
    query: str
    url: str


# -------------------------------------------------------------------------
# Tools Setup
# -------------------------------------------------------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "scrape_url",
            "description": "Scrapes a webpage and returns its markdown equivalent",
            "parameters": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the webpage to scrape",
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "Flag to indicate whether to use cached data",
                    },
                },
                "additionalProperties": False,
            },
        },
    }
]


def execute_scrape_tool(url: str, use_cache: bool = True) -> str:
    """
    Execute the scrape_url tool by calling the external scraping service
    """
    try:
        params = {
            "url": url,
            "force_fetch": not use_cache,
        }
        # Use host.docker.internal instead of localhost when running in Docker
        scraper_url = "http://host.docker.internal:8084/scrape"
        response = requests.get(scraper_url, params=params)
        response.raise_for_status()

        scraped_data = response.json()
        return scraped_data["markdown"]
    except requests.RequestException as e:
        logger.error(f"Error calling scraping service for URL {url}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error scraping URL: {str(e)}")


# -------------------------------------------------------------------------
# /research Endpoint
# -------------------------------------------------------------------------
@app.post("/research", summary="Research a webpage to answer a query")
def research_webpage(request: ResearchRequest):
    """
    Given a URL and a query, this endpoint uses the external scraping service to get webpage content
    and then asks GPT‑4o to answer or extract information based on that content.

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

    # Step 2: Prepare messages for GPT-4o call
    developer_message = {
        "role": "developer",
        "content": [
            {
                "type": "text",
                "text": (
                    "You are a webpage researcher. You are provided with the content of a webpage and a user query. "
                    "Analyze the webpage content to extract or answer the query. If the information is missing, state that it is not available. "
                    "Return your answer in clear markdown format with any references to the source page as needed."
                ),
            }
        ],
    }

    user_message = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"Query: {request.query}\n\nWebpage URL: {request.url}\n\nWebpage Content:\n\n{scraped_content}",
            }
        ],
    }

    messages = [developer_message, user_message]

    # Step 3: Call the GPT-4o model
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "text"},
            temperature=0.2,
            tools=tools,  # Add tools to the model call
        )
        answer_text = response.choices[0].message.content
        logger.info(
            f"GPT-4o answered the research query (correlation_id: {correlation_id})"
        )
    except Exception as e:
        logger.error(f"Error in processing GPT-4o request: {str(e)}", exc_info=True)
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
