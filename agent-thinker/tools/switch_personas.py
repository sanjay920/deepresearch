import json
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You have access to the following tools. Come up with a plan that leverages these tools.
[
    {
      "type": "function",
      "function": {
        "name": "scrape_urls",
        "strict": True,
        "parameters": {
          "type": "object",
          "required": [
            "urls",
            "use_cache"
          ],
          "properties": {
            "urls": {
              "type": "array", 
              "items": {
                "type": "string",
                "description": "A single URL of a webpage"
              },
              "description": "An array of string URLs of the webpages to scrape"
            },
            "use_cache": {
              "type": "boolean",
              "description": "Flag to indicate whether to use cached data (default is true). Set to false when fetching a webpage with live info such as espn.com/nba/scoreboard or anything with dynamic content"
            }
          },
          "additionalProperties": False
        },
        "description": "Scrapes a webpage and returns its markdown equivalent"
      }
    },
    {
      "type": "function",
      "function": {
        "name": "google_search",
        "description": "Performs a Google search with the specified query and returns results.",
        "parameters": {
          "type": "object",
          "required": [
            "q"
          ],
          "properties": {
            "q": {
              "type": "string",
              "description": "The search query string."
            }
          },
          "additionalProperties": False
        },
        "strict": True
      }
    }
  ]

Today's date is {datetime.now().strftime('%B %d, %Y')}. Do not simulate answers - your responsibility is to think and plan."""


def switch_personas_call(switch_to, conversation, thinking_level="high"):
    """
    Implements the switch_personas pipeline from the notebook.

    Args:
        switch_to (str): Must be "thinker" (as per schema)
        conversation (Conversation): The current conversation context
        thinking_level (str): One of "high", "medium", "low"

    Returns:
        str: The response from the thinker persona as a JSON string
    """
    # Prefix for all messages to the thinker
    user_prefix = "This is the conversation so far. The agent has decided to think. That means you are the assistant's subconscience. Any question you ask - tell the assistant to ask the user. You are talking to the assistant, not the user.\n"

    # Get the conversation history from the current context
    conversation_history = conversation.format_conversation()
    input_message = user_prefix + conversation_history

    # Response format schema
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "action_schema",
            "strict": True,
            "schema": {
                "type": "object",
                "required": ["action", "text", "respond_to_user"],
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text of the questions or the text of a detailed plan.",
                    },
                    "action": {
                        "enum": ["questions", "plan"],
                        "type": "string",
                        "description": "Defines the type of action whether it is a set of questions or a detailed plan.",
                    },
                    "respond_to_user": {
                        "type": "boolean",
                        "description": "Normally, you are responding to the assistant. In the case you are synthesizing the final answer you can choose to bypass this and respond directly to the user.",
                    },
                },
                "additionalProperties": False,
            },
        },
    }

    # Make the API call
    response = client.chat.completions.create(
        model="o3-mini",
        messages=[{"role": "user", "content": input_message}],
        response_format=response_format,
        reasoning_effort=thinking_level,
    )

    # Return the response as a JSON string (not a dict)
    return response.choices[0].message.content
