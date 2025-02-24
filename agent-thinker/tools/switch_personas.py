import json
from openai import OpenAI
import os
from datetime import datetime
from conversation import Conversation  # Explicitly import Conversation class

# Initialize OpenAI client with API key from environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# System prompt instructing the thinker persona on how to respond
SYSTEM_PROMPT = f"""Formatting re-enabled
You are the assistant's subconscious, tasked with planning and thinking to address the user's request. You have access to the following tools:

Tools:
[
    {{
        "type": "function",
        "function": {{
            "name": "scrape_urls",
            "strict": True,
            "parameters": {{
                "type": "object",
                "required": ["urls", "use_cache"],
                "properties": {{
                    "urls": {{
                        "type": "array",
                        "items": {{"type": "string"}},
                        "description": "An array of URLs to scrape"
                    }},
                    "use_cache": {{
                        "type": "boolean",
                        "description": "Whether to use cached data (default: true). Set to false for dynamic content."
                    }}
                }},
                "additionalProperties": False
            }},
            "description": "Scrapes webpages and returns their markdown equivalent"
        }}
    }},
    {{
        "type": "function",
        "function": {{
            "name": "google_search",
            "parameters": {{
                "type": "object",
                "required": ["q"],
                "properties": {{
                    "q": {{"type": "string", "description": "The search query string"}}
                }},
                "additionalProperties": False
            }},
            "description": "Performs a Google search and returns results"
        }}
    }}
]

**Instructions:**
- Review the conversation history provided below.
- For multi-step or data-intensive requests (e.g., research reports), set 'action' to 'plan' and:
  - Provide a 'text' field with a natural language description of the plan in Markdown.
  - Include a 'steps' field listing specific tool calls with their parameters (e.g., google_search, scrape_urls).
  - Example:
    ```json
    {{
        "action": "plan",
        "text": "## Research Plan\\nSearch for AI agent platform reports and scrape relevant sites.",
        "steps": [
            {{"tool": "google_search", "parameters": {{"q": "AI agent platforms research report"}}}},
            {{"tool": "scrape_urls", "parameters": {{"urls": ["https://example.com"], "use_cache": true}}}}
        ],
        "respond_to_user": false
    }}
    ```
- For unclear or incomplete requests, set 'action' to 'questions', provide questions in 'text' in Markdown, and set 'respond_to_user' to false.
- For simple queries (e.g., schedules), propose a concise plan with a single step if sufficient.
- Do not use scratchpad tools here; let the agent handle data storage.
- Today's date is {datetime.now().strftime('%B %d, %Y')}. Use this for time-sensitive queries.
- Keep plans or questions concise and directly aligned with the user's request.
"""


def switch_personas_call(
    switch_to: str, conversation: Conversation, thinking_level: str = "high"
) -> str:
    """
    Switches the assistant to the 'thinker' persona to generate a plan or questions.

    Args:
        switch_to (str): The persona to switch to (must be "thinker").
        conversation (Conversation): The current conversation context, an instance of the Conversation class.
        thinking_level (str): Level of thinking effort ("high", "medium", "low").

    Returns:
        str: JSON string containing the thinker's response (plan or questions).

    Raises:
        ValueError: If switch_to is not "thinker".
    """
    if switch_to != "thinker":
        raise ValueError("Only switching to 'thinker' is supported.")

    # Get conversation history for context using the Conversation class method
    conversation_history = conversation.format_conversation()
    user_message = f"Conversation history:\n{conversation_history}"

    # Define the corrected response format schema based on your example
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "thinker_response",
            "strict": False,  # Relaxed strictness to avoid overly restrictive validation
            "schema": {
                "type": "object",
                "required": ["action", "text", "respond_to_user"],
                "properties": {
                    "action": {
                        "enum": ["plan", "questions"],
                        "type": "string",
                        "description": "Type of response: 'plan' for a detailed plan, 'questions' for clarifications.",
                    },
                    "text": {
                        "type": "string",
                        "description": "Description of the plan or questions to ask, in Markdown.",
                    },
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "oneOf": [
                                {
                                    "properties": {
                                        "tool": {
                                            "const": "google_search",
                                            "type": "string",
                                            "description": "Tool to perform a Google search.",
                                        },
                                        "parameters": {
                                            "type": "object",
                                            "required": ["q"],
                                            "properties": {
                                                "q": {
                                                    "type": "string",
                                                    "description": "The search query string.",
                                                }
                                            },
                                            "additionalProperties": False,
                                        },
                                    },
                                    "required": ["tool", "parameters"],
                                    "additionalProperties": False,
                                },
                                {
                                    "properties": {
                                        "tool": {
                                            "const": "scrape_urls",
                                            "type": "string",
                                            "description": "Tool to scrape webpages.",
                                        },
                                        "parameters": {
                                            "type": "object",
                                            "required": ["urls", "use_cache"],
                                            "properties": {
                                                "urls": {
                                                    "type": "array",
                                                    "items": {"type": "string"},
                                                    "description": "An array of URLs to scrape.",
                                                },
                                                "use_cache": {
                                                    "type": "boolean",
                                                    "description": "Whether to use cached data (default: true).",
                                                },
                                            },
                                            "additionalProperties": False,
                                        },
                                    },
                                    "required": ["tool", "parameters"],
                                    "additionalProperties": False,
                                },
                            ],
                            "description": "A step in the plan specifying a tool and its parameters.",
                        },
                        "description": "List of tool calls for the plan. Include when action is 'plan'.",
                    },
                    "respond_to_user": {
                        "type": "boolean",
                        "description": "Whether this response is for the user (false by default).",
                    },
                },
                "additionalProperties": False,
            },
        },
    }

    try:
        # Call the OpenAI API with system prompt as 'developer' message and user message with history
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "developer", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format=response_format,
            reasoning_effort=thinking_level,
            max_completion_tokens=5000,  # Increased to handle complex report planning
        )
        return response.choices[0].message.content
    except Exception as e:
        error_msg = f"Failed to switch personas: {str(e)}"
        return json.dumps({"error": error_msg})
