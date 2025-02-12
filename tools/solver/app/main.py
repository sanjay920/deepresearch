import os
import json
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from openai import OpenAI
import httpx
from datetime import datetime
import secrets


# ------------------------------------------------------------------------------
# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------


# Define a filter to inject correlation IDs (as before)
class CorrelationIDFilter(logging.Filter):
    """Adds a correlation_id attribute to log records."""

    def __init__(self):
        super().__init__()
        self.correlation_id = None

    def filter(self, record):
        if not hasattr(record, "correlation_id"):
            record.correlation_id = getattr(self, "correlation_id", "no_id")
        return True


# New filter to capture all extra attributes that are not part of the reserved set.
class ExtraFilter(logging.Filter):
    RESERVED_ATTRS = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "correlation_id",
    }

    def filter(self, record):
        record.extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in self.RESERVED_ATTRS and not k.startswith("_")
        }
        return True


# Updated custom formatter that appends the extras from the filter into the log message.
class CustomFormatter(logging.Formatter):
    """
    Custom formatter that handles missing correlation IDs gracefully and includes extras.
    """

    def format(self, record):
        # Ensure correlation_id is set
        if not hasattr(record, "correlation_id"):
            main_logger = logging.getLogger("main")
            if hasattr(main_logger, "correlation_id"):
                record.correlation_id = main_logger.correlation_id
            else:
                record.correlation_id = "no_id"

        base_msg = super().format(record)
        if hasattr(record, "extras") and record.extras:
            extras_str = " | ".join(f"{k}={v}" for k, v in record.extras.items())
            return f"{base_msg} | {extras_str}"
        else:
            return base_msg


# Set up root logger with our custom formatter and filters
formatter = CustomFormatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# Our application-specific logger gets both the correlation ID filter and the extra filter
logger = logging.getLogger(__name__)
logger.addFilter(CorrelationIDFilter())
logger.addFilter(ExtraFilter())
correlation_filter = logger.filters[0]

# ------------------------------------------------------------------------------
# FASTAPI SETUP
# ------------------------------------------------------------------------------
app = FastAPI(
    title="Solver Microservice",
    description="A microservice that takes an objective and research plan, executes them using OpenAI, and returns a string response.",
    version="1.0.0",
)

# ------------------------------------------------------------------------------
# OPENAI CLIENT SETUP
# ------------------------------------------------------------------------------
if "OPENAI_API_KEY" not in os.environ:
    raise RuntimeError("OPENAI_API_KEY is not set. Please set it or use .env.sample.")

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# We default the broker host to 'localhost', but you can override via environment.
BROKER_HOST = os.getenv("BROKER_HOST", "localhost")

# Increase timeout for broker calls
BROKER_TIMEOUT = 3600.0  # 3600 seconds (1 hour) timeout


# ------------------------------------------------------------------------------
# REQUEST/RESPONSE MODELS
# ------------------------------------------------------------------------------
class SolveRequest(BaseModel):
    objective: str = Field(..., description="The main objective (e.g. user request).")
    research_plan: list[str] = Field(
        ..., description="List of steps to achieve the objective."
    )


# ------------------------------------------------------------------------------
# ENDPOINT
# ------------------------------------------------------------------------------
@app.post("/solve", summary="Execute the research plan")
async def solve(request: SolveRequest) -> str:
    """
    This endpoint takes a JSON body with:
      - objective: str
      - research_plan: list of strings (the steps)

    It constructs a conversation for the 'o3-mini' model, passing:
      - A 'developer' role message with instructions
      - A 'user' role message that contains the JSON {objective, research_plan}
        exactly as text.

    The endpoint will continue the conversation with OpenAI, handling any tool
    calls until a final text response is received.
    """
    # Validate input
    if not request.objective.strip():
        raise HTTPException(status_code=400, detail="Objective cannot be empty")

    if not request.research_plan:
        raise HTTPException(status_code=400, detail="Research plan cannot be empty")

    # --------------------------------------------------------------------------
    # 1. Generate correlation_id for logs
    # --------------------------------------------------------------------------
    correlation_id = f"req_{secrets.token_hex(6)}"
    correlation_filter.correlation_id = correlation_id
    logging.getLogger("main").correlation_id = correlation_id

    # --------------------------------------------------------------------------
    # 2. Prepare the conversation messages
    # --------------------------------------------------------------------------
    # The "developer" role message
    developer_msg = {
        "role": "developer",
        "content": [
            {
                "text": (
                    "Execute the given objective and research plan. "
                    "Ensure a high-quality response with sources cited in a references section."
                ),
                "type": "text",
            }
        ],
    }

    # The "user" role message, containing the objective & plan as text with timestamp
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_msg = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"[{current_time}] "
                + json.dumps(
                    {
                        "objective": request.objective,
                        "research_plan": request.research_plan,
                    },
                    indent=2,
                ),
            }
        ],
    }
    logger.info(
        "User message prepared",
        extra={
            "correlation_id": correlation_id,
            "user_message": user_msg,
        },
    )

    # We'll also specify the overall set of "tools" in the call
    tools = [
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
                            "description": (
                                "The query/ask for the information broker. "
                                "Must be a complete sentence - something descriptive enough for them to get context"
                            ),
                        }
                    },
                    "additionalProperties": False,
                },
                "description": (
                    "An information broker that takes in a query and searches the web "
                    "using Google to provide an answer."
                ),
            },
        }
    ]

    # This matches your notebook's usage
    messages = [developer_msg, user_msg]

    # --------------------------------------------------------------------------
    # 3. Main conversation loop
    # --------------------------------------------------------------------------
    final_text_output = None
    max_iterations = 50  # Prevent infinite loops
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        logger.info(
            f"Starting iteration {iteration}/{max_iterations}",
            extra={
                "correlation_id": correlation_id,
                "message_count": len(messages),
                "objective": (
                    request.objective[:100] + "..."
                    if len(request.objective) > 100
                    else request.objective
                ),
            },
        )

        try:
            response = client.chat.completions.create(
                model="o3-mini",
                messages=messages,
                response_format={"type": "text"},
                reasoning_effort="high",
                tools=tools,
            )
        except Exception as e:
            logger.exception(
                f"Error calling OpenAI in iteration {iteration}",
                extra={"correlation_id": correlation_id},
            )
            raise HTTPException(status_code=500, detail=f"OpenAI error: {str(e)}")

        # Log the response type we got
        logger.info(
            f"OpenAI response received for iteration {iteration}",
            extra={
                "correlation_id": correlation_id,
                "finish_reason": response.choices[0].finish_reason,
                "token_usage": (
                    response.usage.total_tokens if response.usage else "unknown"
                ),
            },
        )

        # If we got a final response, break the loop
        if response.choices[0].finish_reason != "tool_calls":
            final_text_output = response.choices[0].message.content
            logger.info(
                "Received final text response",
                extra={
                    "correlation_id": correlation_id,
                    "content_length": len(final_text_output),
                    "iteration": iteration,
                    "total_messages": len(messages),
                },
            )
            break

        # Handle tool calls
        tool_calls = response.choices[0].message.tool_calls
        logger.info(
            f"Processing tool calls for iteration {iteration}",
            extra={
                "correlation_id": correlation_id,
                "tool_calls_count": len(tool_calls),
                "total_messages_so_far": len(messages),
            },
        )

        # Add assistant's message with tool calls to conversation
        messages.append(
            {"role": "assistant", "content": None, "tool_calls": tool_calls}
        )

        # Process each tool call
        for tool_call_idx, tool_call in enumerate(tool_calls, 1):
            logger.info(
                f"Processing tool call {tool_call_idx}/{len(tool_calls)}",
                extra={
                    "correlation_id": correlation_id,
                    "tool_name": tool_call.function.name,
                    "tool_id": tool_call.id,
                    "tool_args": tool_call.function.arguments,
                    "iteration": iteration,
                },
            )

            if tool_call.function.name == "query_information_broker":
                args = json.loads(tool_call.function.arguments)
                broker_url = f"http://{BROKER_HOST}:8081/generate"

                try:
                    async with httpx.AsyncClient() as http_client:
                        logger.info(
                            "Calling information broker",
                            extra={
                                "correlation_id": correlation_id,
                                "broker_url": broker_url,
                                "query": args["query"],
                                "tool_call_idx": tool_call_idx,
                                "iteration": iteration,
                                "request_body": {"prompt": args["query"]},
                            },
                        )
                        broker_response = await http_client.post(
                            broker_url,
                            json={"prompt": args["query"]},
                            timeout=BROKER_TIMEOUT,  # Use increased timeout
                        )
                    broker_data = broker_response.json()

                    # Get response preview - first 500 chars
                    response_str = json.dumps(broker_data)
                    response_preview = (
                        response_str[:500] + "..."
                        if len(response_str) > 500
                        else response_str
                    )

                    logger.info(
                        "Received broker response",
                        extra={
                            "correlation_id": correlation_id,
                            "response_length": len(response_str),
                            "response_preview": response_preview,
                            "tool_call_idx": tool_call_idx,
                            "iteration": iteration,
                        },
                    )
                except Exception as be:
                    logger.exception(
                        "Error calling broker tool",
                        extra={"correlation_id": correlation_id},
                    )
                    raise HTTPException(
                        status_code=500, detail=f"Broker error: {str(be)}"
                    )

                # Add tool response to conversation with timestamp
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"[{current_time}] " + json.dumps(broker_data),
                    }
                )

        logger.info(
            f"Completed iteration {iteration}",
            extra={
                "correlation_id": correlation_id,
                "total_messages": len(messages),
                "tools_processed": len(tool_calls),
            },
        )

    if not final_text_output:
        logger.warning(
            "No final text output generated",
            extra={
                "correlation_id": correlation_id,
                "total_iterations": iteration,
                "total_messages": len(messages),
            },
        )
        final_text_output = (
            "No content was generated after maximum iterations. "
            "Possibly an error occurred or the response was empty."
        )

    return final_text_output
