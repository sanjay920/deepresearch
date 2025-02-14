import os
import json
import logging
from typing import Optional, List, Dict
from datetime import datetime
import secrets

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from openai import OpenAI
import httpx

# ------------------------------------------------------------------------------
# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------


# Define a filter to inject correlation IDs
class CorrelationIDFilter(logging.Filter):
    """Adds a correlation_id attribute to log records."""

    def __init__(self):
        super().__init__()
        self.correlation_id = None

    def filter(self, record):
        if not hasattr(record, "correlation_id"):
            record.correlation_id = getattr(self, "correlation_id", "no_id")
        return True


# Filter to capture all extra attributes
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


# Custom formatter that handles missing correlation IDs and includes extras
class CustomFormatter(logging.Formatter):
    """Custom formatter that handles missing correlation IDs gracefully and includes extras."""

    def format(self, record):
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
        return base_msg


# Set up root logger
formatter = CustomFormatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s"
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.handlers.clear()
root_logger.addHandler(handler)
root_logger.setLevel(logging.INFO)

# Application-specific logger setup
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

# Default broker host to 'localhost', can be overridden via environment
BROKER_HOST = os.getenv("BROKER_HOST", "localhost")
BROKER_TIMEOUT = 3600.0  # 1 hour timeout for broker calls


# ------------------------------------------------------------------------------
# REQUEST/RESPONSE MODELS
# ------------------------------------------------------------------------------
class SolveRequest(BaseModel):
    objective: str = Field(..., description="The main objective (e.g. user request).")
    research_plan: List[str] = Field(
        ..., description="List of steps to achieve the objective."
    )
    conversation_history: Optional[List[Dict]] = Field(
        default=[], description="Previous conversation messages for context."
    )


# ------------------------------------------------------------------------------
# ENDPOINT
# ------------------------------------------------------------------------------
@app.post("/solve", summary="Execute the research plan")
async def solve(request: SolveRequest) -> str:
    """
    Execute a research plan to achieve an objective.

    Takes a JSON body with:
    - objective: str
    - research_plan: list of strings (the steps)
    - conversation_history: list of dictionaries containing previous conversation messages

    Returns the final response as a string (typically in Markdown format).
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
    # The "developer" role message with instructions
    developer_msg = {
        "role": "developer",
        "content": [
            {
                "text": (
                    "Execute the given objective and research plan one step at a time. "
                    "Ensure a high-quality response with sources cited in a references section. "
                    "Keep in mind that the query_information_broker cannot handle complex queries; "
                    "ask it to perform only one step in your research plan at a time and adjust as needed. "
                    "Feel free to use multiple calls to the tool."
                ),
                "type": "text",
            }
        ],
    }

    # Add current time and construct the user message
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_msg = {
        "role": "user",
        "content": f"Current time: {current_time}\nObjective: {request.objective}\nPlan: {json.dumps(request.research_plan)}",
    }

    logger.info(
        "User message prepared",
        extra={
            "correlation_id": correlation_id,
            "user_message": user_msg,
        },
    )

    # Tool definitions
    tools = [
        {
            "type": "function",
            "function": {
                "name": "query_information_broker",
                "description": "An information broker that takes in a query and searches the web using Google to provide an answer.",
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
                "strict": True,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "load_webpage_and_query",
                "description": "Specialist at loading in a specific webpage and answering a query about it.",
                "parameters": {
                    "type": "object",
                    "required": ["query", "url"],
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to be answered regarding the webpage.",
                        },
                        "url": {
                            "type": "string",
                            "description": "The URL of the webpage to be loaded.",
                        },
                    },
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    ]

    # Build the complete message list: developer instruction, conversation history, current user message
    messages = [developer_msg] + (request.conversation_history or []) + [user_msg]

    # --------------------------------------------------------------------------
    # 3. Main conversation loop
    # --------------------------------------------------------------------------
    final_text_output = None
    max_iterations = 100  # Prevent infinite loops
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
                            timeout=BROKER_TIMEOUT,
                        )
                    broker_data = broker_response.json()

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
                        "content": f"[{current_time}] {json.dumps(broker_data)}",
                    }
                )

            elif tool_call.function.name == "load_webpage_and_query":
                args = json.loads(tool_call.function.arguments)
                webpage_url = f"http://{BROKER_HOST}:8087/research"

                try:
                    async with httpx.AsyncClient() as http_client:
                        logger.info(
                            "Calling webpage researcher",
                            extra={
                                "correlation_id": correlation_id,
                                "webpage_url": webpage_url,
                                "query": args["query"],
                                "url": args["url"],
                                "tool_call_idx": tool_call_idx,
                                "iteration": iteration,
                                "request_body": {
                                    "query": args["query"],
                                    "url": args["url"],
                                },
                            },
                        )
                        webpage_response = await http_client.post(
                            webpage_url,
                            json={"query": args["query"], "url": args["url"]},
                            timeout=BROKER_TIMEOUT,
                        )
                        webpage_data = webpage_response.json()

                        # Handle various error responses
                        if webpage_response.status_code != 200:
                            error_msg = webpage_data.get("detail", {})
                            if isinstance(error_msg, dict):
                                error_type = error_msg.get("error", "unknown_error")
                                error_message = error_msg.get(
                                    "message", "Unknown error occurred"
                                )
                            else:
                                error_type = "unknown_error"
                                error_message = str(error_msg)

                            if error_type == "authentication_failed":
                                error_content = (
                                    "The webpage research tool is currently unavailable due to "
                                    "authentication issues. Please try an alternative approach or "
                                    "contact support if this persists."
                                )
                            else:
                                error_content = (
                                    f"Webpage research failed: {error_message}"
                                )

                            logger.warning(
                                error_content,
                                extra={
                                    "correlation_id": correlation_id,
                                    "error_type": error_type,
                                    "tool_call_idx": tool_call_idx,
                                    "iteration": iteration,
                                },
                            )
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_content}",
                                }
                            )
                            continue

                        # Process successful response
                        response_str = json.dumps(webpage_data)
                        response_preview = (
                            response_str[:500] + "..."
                            if len(response_str) > 500
                            else response_str
                        )

                        logger.info(
                            "Received webpage researcher response",
                            extra={
                                "correlation_id": correlation_id,
                                "response_length": len(response_str),
                                "response_preview": response_preview,
                                "tool_call_idx": tool_call_idx,
                                "iteration": iteration,
                            },
                        )

                        # Add tool response to conversation with timestamp
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"[{current_time}] {json.dumps(webpage_data)}",
                            }
                        )

                except Exception as we:
                    error_msg = f"Webpage researcher error: {str(we)}"
                    logger.exception(
                        error_msg,
                        extra={"correlation_id": correlation_id},
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {error_msg}",
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
