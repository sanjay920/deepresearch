import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import json
import httpx
from typing import Optional
from datetime import datetime


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
    current_date = datetime.now().strftime("%B %d, %Y %H:%M:%S")
    system_message_content = [
        {
            "text": (
                f"As a reminder, today's date is {current_date}. Avoid using ambiguous terms like 'today' or 'yesterday'\n\n"
                "You are a routing agent tasked with determining the complexity of user queries and providing appropriate responses. "
                "Your job is to analyze the query and decide whether it is complex or straightforward. Follow these steps:\n\n"
                "1. Analyze the Query:\n"
                "   - If the query is complex, ambiguous, or open-ended, return:\n"
                "     ```json\n"
                "     {\n"
                '       "is_complex": true\n'
                "     }\n"
                "     ```\n"
                "     Do not provide any additional response. This signals that the query should be routed to the planning assistant.\n"
                "   - If the query is straightforward, proceed to step 2.\n\n"
                "2. Provide a Response:\n"
                "   You have two options for straightforward queries:\n"
                "   a. **Direct Answer:** Generate your own answer and return:\n"
                "      ```json\n"
                "      {\n"
                '        "is_complex": false,\n'
                '        "response": "your response here"\n'
                "      }\n"
                "      ```\n"
                "   b. **Use the query_information_broker Tool:**\n"
                "      - Ensure the query you send to `query_information_broker` is written as a complete, respectful sentence.\n"
                "      - After receiving the tool's output, evaluate it:\n"
                "         - **If the tool's output is fully sufficient as the final answer** (i.e. it includes all necessary information and follows the required citation format), return:\n"
                "           ```json\n"
                '           {"pass": true}\n'
                "           ```\n"
                "           This signals the upstream system to use the tool's answer.\n"
                "         - **If the tool's output is not appropriate** (e.g. it is incomplete, lacks citations, or does not meet the required standards), ignore the tool's output and generate your own answer. In that case, return your answer in the following format:\n"
                "           ```json\n"
                "           {\n"
                '             "is_complex": false,\n'
                '             "response": "your response here"\n'
                "           }\n"
                "           ```\n\n"
                "3. Citation Guidelines:\n"
                "   - If citations are provided or required, ensure they follow this format:\n"
                "     - **Example Entry:**\n"
                "       - **Dried or Dehydrated Products:** Including items specifically marked as dehydrated.[1, 2, 3, 4]\n"
                "       - **Frozen or Chilled Products:** Including items in the Frozen/Chilled section.[1, 3, 5]\n"
                "     - The answer might include:\n"
                "       ```\n"
                "       Sources:\n"
                "       1. [wikimedia.org](https://tinyurl.com/2cobgzpz)\n"
                "       2. [ncrfsma.org](https://tinyurl.com/269njje2)\n"
                "       ```\n\n"
                "4. Output Format:\n"
                "   - For complex queries:\n"
                "     ```json\n"
                "     {\n"
                '       "is_complex": true\n'
                "     }\n"
                "     ```\n"
                "   - For simple queries answered directly:\n"
                "     ```json\n"
                "     {\n"
                '       "is_complex": false,\n'
                '       "response": "your response here"\n'
                "     }\n"
                "     ```\n"
                "   - For queries answered via the tool (when the tool's output is fully sufficient - meaning full, complete sentences with all the info that you would expect from a good assistant):\n"
                "     ```json\n"
                "     {\n"
                '       "pass": true\n'
                "     }\n"
                "     ```\n\n"
                "Notes:\n"
                "- Always ensure your query to the tool is a complete, respectful sentence.\n"
                "- Only output the specified JSON object with no additional commentary.\n"
                "- **Critical:** When using the tool, if the tool's response is inappropriate for any reason, do not use it. Instead, generate your own answer in the direct response format."
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

        # Handle the "pass" case by processing the tool output
        if parsed_response.get("pass"):
            if not response.choices[0].message.tool_calls:
                raise ValueError("Pass response received but no tool output found")

            # Get the last tool response
            last_tool_message = next(
                msg for msg in reversed(messages) if msg["role"] == "tool"
            )

            # Extract content and remove search queries section
            tool_content = last_tool_message["content"]
            if isinstance(tool_content, list):
                tool_content = tool_content[0]["text"]
            elif isinstance(tool_content, str):
                try:
                    # Try to parse if it's a JSON string
                    parsed_tool_content = json.loads(tool_content)
                    if (
                        isinstance(parsed_tool_content, dict)
                        and "response" in parsed_tool_content
                    ):
                        tool_content = parsed_tool_content["response"]
                except json.JSONDecodeError:
                    # If not JSON, use as-is
                    pass

            clean_content = tool_content.split("Search Queries:")[0].strip()

            # Return modified response with the cleaned tool content
            parsed_response = {"is_complex": False, "response": clean_content}

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
