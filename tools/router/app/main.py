import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import json
import httpx
from typing import Optional


# Configure logging with a more robust format
class CustomFormatter(logging.Formatter):
    """Custom formatter that handles missing correlation IDs gracefully"""

    def format(self, record):
        if not hasattr(record, "correlation_id"):
            # Get correlation ID from the main logger if available
            main_logger = logging.getLogger("main")
            if hasattr(main_logger, "correlation_id"):
                record.correlation_id = main_logger.correlation_id
            else:
                record.correlation_id = "no_id"
        return super().format(record)


# Configure logging
formatter = CustomFormatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s"
)

# Remove any existing handlers
logging.getLogger().handlers.clear()

# Create and configure handler
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# Configure our application logger
logger = logging.getLogger(__name__)


# Add correlation ID filter
class CorrelationIDFilter(logging.Filter):
    """Adds correlation ID to log records"""

    def __init__(self):
        super().__init__()
        self.correlation_id = None

    def filter(self, record):
        if not hasattr(record, "correlation_id"):
            record.correlation_id = getattr(self, "correlation_id", "no_id")
        return True


logger.addFilter(CorrelationIDFilter())
correlation_filter = logger.filters[0]

app = FastAPI(
    title="Router Microservice",
    description="A microservice API that routes user queries based on complexity.",
    version="1.0.0",
)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Get broker host from environment variable, default to localhost
BROKER_HOST = os.getenv("BROKER_HOST", "localhost")


class RouteRequest(BaseModel):
    message: str


@app.post("/route", summary="Route user query")
async def route_query(request: RouteRequest):
    """
    Analyze the user's query and route it accordingly.
    The response must follow this JSON format:

    ```json
    {
      "is_complex": [true/false],
      "response/routing": [response or indicate routing to planning assistant]
    }
    ```
    """
    # Generate correlation ID for this request
    correlation_id = f"req_{os.urandom(6).hex()}"
    correlation_filter.correlation_id = correlation_id

    # Store correlation ID at module level for other loggers to access
    logging.getLogger("main").correlation_id = correlation_id

    # Set correlation ID for httpx logger
    httpx_logger = logging.getLogger("httpx")
    if not any(isinstance(f, CorrelationIDFilter) for f in httpx_logger.filters):
        httpx_logger.addFilter(CorrelationIDFilter())
    for f in httpx_logger.filters:
        if isinstance(f, CorrelationIDFilter):
            f.correlation_id = correlation_id

    logger.info(
        f"Received routing request",
        extra={
            "correlation_id": correlation_id,
            "message_length": len(request.message),
        },
    )

    # Define the system message as a list of content items (each with text and type)
    system_message_content = [
        {
            "text": (
                "You are a routing agent tasked with determining the complexity of user queries and providing appropriate responses. "
                "If the user's query is complex and challenging, route it to the planning assistant. For less complex queries, utilize available functions to provide an immediate response. "
                "If you choose to use the query_information_broker tool, the query you give it must consist of complete sentences - you dont want to disrespect your colleague. "
                "If you do call query_information_broker, make sure to include citations in your final response back to the user the same way the query_information_broker does citations - here's an example:\n\n"
                "*   **Dried or Dehydrated Products:** Including items specifically marked as dehydrated.[1, 2, 3, 4]\n"
                "*   **Frozen or Chilled Products:** Including items in the Frozen/Chilled section.[1, 3, 5]\n\n"
                'The search results indicate that you can request copies of these standards from the "Processed Products Standardization and Inspection Branch, '
                'Fruit and Vegetable Division, AMS, U. S. Department of Agriculture, Washington 25, D. C."[1]\n\n\n'
                "Sources:\n"
                "1. [wikimedia.org](https://tinyurl.com/2cobgzpz)\n"
                "2. [ncrfsma.org](https://tinyurl.com/269njje2)\n...Additionally Sources Here\n\n"
                "# Steps\n\n"
                "1. Analyze the user's query:\n"
                "   - Determine if the query is complex or straightforward.\n"
                "   - Use complexity cues (e.g., open-ended questions, ambiguous terms).\n\n"
                "2. Route or respond:\n"
                "   - If complex, set is_complex to true with no response field.\n"
                "   - If straightforward, provide answer in the response field.\n\n"
                "# Output Format\n\n"
                "Your output must be in the following JSON format (and nothing else):\n\n"
                "For complex queries:\n"
                "```json\n"
                "{\n"
                '  "is_complex": true\n'
                "}\n"
                "```\n\n"
                "For simple queries:\n"
                "```json\n"
                "{\n"
                '  "is_complex": false,\n'
                '  "response": "your response here"\n'
                "}\n"
                "```\n\n"
                "# Notes\n\n"
                "- Ensure clarity and precision in determining the complexity of queries.\n"
                "- For complex queries, only return is_complex=true with no response field.\n"
                "- For simple queries, provide the response in the response field."
            ),
            "type": "text",
        }
    ]

    # Construct the messages list
    messages = [
        {
            "role": "system",
            "content": system_message_content,
        },
        {
            "role": "user",
            "content": [
                {
                    "text": request.message,
                    "type": "text",
                }
            ],
        },
    ]

    logger.debug(
        "Sending request to OpenAI",
        extra={
            "correlation_id": correlation_id,
            "model": "gpt-4o",
            "message_count": len(messages),
        },
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"},
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "query_information_broker",
                        "strict": True,
                        "parameters": {
                            "type": "object",
                            "required": ["query"],
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The query/ask for the information broker. Must be a complete sentence - something descriptive enough for them to get context",
                                }
                            },
                            "additionalProperties": False,
                        },
                        "description": "An information broker that takes in a query and searches the web using Google to provide an answer.",
                    },
                }
            ],
            temperature=0.07,
            max_completion_tokens=10831,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )

        # Add logging for tool calls
        if response.choices[0].message.tool_calls:
            logger.info(
                "Processing tool calls",
                extra={
                    "correlation_id": correlation_id,
                    "tool_name": response.choices[0]
                    .message.tool_calls[0]
                    .function.name,
                },
            )

            tool_call = response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "query_information_broker":
                # Parse the function arguments
                args = json.loads(tool_call.function.arguments)

                # Make request to information broker service using configured host
                broker_url = f"http://{BROKER_HOST}:8081/generate"
                async with httpx.AsyncClient() as http_client:
                    logger.info(
                        "Making request to information broker",
                        extra={
                            "correlation_id": correlation_id,
                            "broker_url": broker_url,
                        },
                    )
                    broker_response = await http_client.post(
                        broker_url, json={"prompt": args["query"]}, timeout=30.0
                    )
                    broker_data = broker_response.json()

                # Create a follow-up message with the broker's response
                messages.append(
                    {"role": "assistant", "content": None, "tool_calls": [tool_call]}
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(broker_data),
                    }
                )

                # Get final response from OpenAI
                final_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.07,
                    max_completion_tokens=10831,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                )
                content = final_response.choices[0].message.content

        else:
            content = response.choices[0].message.content

        if content is None:
            raise ValueError("No content received from OpenAI")

        parsed_response = json.loads(content)
        logger.info(
            "Successfully processed request",
            extra={
                "correlation_id": correlation_id,
                "is_complex": parsed_response.get("is_complex"),
            },
        )

    except Exception as e:
        logger.exception(
            "Error processing query",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise HTTPException(status_code=500, detail=str(e))

    return parsed_response
