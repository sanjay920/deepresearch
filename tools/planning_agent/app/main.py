import os
import json
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI


# -------------------------------------------------------------------------
# Logging Setup (inspired by your router sample)
# -------------------------------------------------------------------------
class CustomFormatter(logging.Formatter):
    """Custom formatter that adds a correlation_id to log records."""

    def format(self, record):
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "no_id"
        return super().format(record)


formatter = CustomFormatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s"
)

# Remove any existing handlers and set up our own
logging.getLogger().handlers.clear()
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------
# FastAPI App Setup
# -------------------------------------------------------------------------
app = FastAPI(
    title="Planning Assistant Microservice",
    description=(
        "A microservice that uses OpenAI's API (model: o3-mini) to generate a "
        "JSON response for planning assistant queries. The output follows a strict "
        "JSON schema."
    ),
    version="1.0.0",
)

# -------------------------------------------------------------------------
# OpenAI Client Initialization (using the new OpenAI client)
# -------------------------------------------------------------------------
try:
    OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
except KeyError:
    logger.error("OPENAI_API_KEY environment variable must be set")
    raise

client = OpenAI(api_key=OPENAI_API_KEY)


# -------------------------------------------------------------------------
# Request Model
# -------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    message: str
    conversation_history: list[dict] = []  # Optional list of previous messages


# -------------------------------------------------------------------------
# /generate Endpoint
# -------------------------------------------------------------------------
@app.post("/generate", summary="Generate planning assistant response")
def generate_plan(request: GenerateRequest):
    """
    Given a user message and conversation history, call OpenAI's API (using model 'o3-mini')
    with a developer message instructing the assistant to follow a strict JSON schema.
    Returns a JSON object.
    """
    correlation_id = f"req_{os.urandom(6).hex()}"
    logger.info("Received planning request", extra={"correlation_id": correlation_id})

    # Prepare the developer instruction with the JSON schema.
    developer_message = {
        "role": "developer",  # Changed from developer to system for better context handling
        "content": [
            {
                "type": "text",
                "text": (
                    "You are a planning assistant. The user may ask a query that requires you to consult with an information broker or a website-specific researcher. "
                    "Analyze the user's request, identify any gaps or ambiguities, and propose a high-level research plan (under 200 words).\n\n"
                    "If there are no gaps or ambiguities, you should not ask clarifying questions. In this case, the clarifications array should be an empty list. \n\n"
                    "Your output must follow this JSON schema:\n"
                    "{\n"
                    '  "name": "planning_assistant",\n'
                    '  "description": "Assist users by analyzing queries and conducting web searches for relevant information.",\n'
                    '  "strict": true,\n'
                    '  "parameters": {\n'
                    '    "type": "object",\n'
                    '    "required": [\n'
                    '      "objective",\n'
                    '      "clarifications",\n'
                    '      "research_plan"\n'
                    "    ],\n"
                    '    "properties": {\n'
                    '      "objective": {\n'
                    '        "type": "string",\n'
                    '        "description": "A summary of your understanding of the query, indicating whether it requires consulting an information broker or a website-specific researcher."\n'
                    "      },\n"
                    '      "research_plan": {\n'
                    '        "type": "array",\n'
                    '        "items": {\n'
                    '          "type": "string",\n'
                    '          "description": "A step or strategy within the research plan."\n'
                    "        },\n"
                    '        "description": "A high-level plan detailing how to conduct the research based on the user\'s query and any identified gaps."\n'
                    "      },\n"
                    '      "clarifications": {\n'
                    '        "type": "array",\n'
                    '        "items": {\n'
                    '          "type": "string",\n'
                    '          "description": "A single clarifying question related to the user\'s query."\n'
                    "        },\n"
                    '        "description": "An array of clarifying questions to better understand the user\'s request."\n'
                    "      }\n"
                    "    },\n"
                    '    "additionalProperties": false\n'
                    "  }\n"
                    "}\n\n"
                    "Do not ask clarifying questions unless the user's request is ambiguous. The output format will always be markdown."
                ),
            }
        ],
    }

    # Convert conversation history to the expected format
    formatted_history = []
    for msg in request.conversation_history:
        formatted_history.append(
            {"role": msg["role"], "content": [{"type": "text", "text": msg["content"]}]}
        )

    # Add the current user message
    user_message = {
        "role": "user",
        "content": [{"type": "text", "text": request.message}],
    }

    # Combine all messages
    messages = [developer_message] + formatted_history + [user_message]

    try:
        response = client.chat.completions.create(
            model="o3-mini",
            messages=messages,
            response_format={"type": "json_object"},
            reasoning_effort="high",
        )
        logger.info(
            "OpenAI response received", extra={"correlation_id": correlation_id}
        )

        # Expect the response JSON string in the first choice.
        content = response.choices[0].message.content
        parsed_output = json.loads(content)
        return parsed_output

    except Exception as e:
        logger.exception(
            "Error generating planning assistant response",
            extra={"correlation_id": correlation_id},
        )
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=80, reload=True)
