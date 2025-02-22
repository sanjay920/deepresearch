import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Tools that DO include scratchpad calls
TOOLS_WITH_SCRATCHPAD = [
    {
        "type": "function",
        "function": {
            "name": "scrape_urls",
            "strict": True,
            "parameters": {
                "type": "object",
                "required": ["urls", "use_cache"],
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "A single URL of a webpage",
                        },
                        "description": "An array of string URLs of the webpages to scrape",
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "Flag to indicate whether to use cached data",
                    },
                },
                "additionalProperties": False,
            },
            "description": "Scrapes a webpage and returns its markdown equivalent",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "switch_personas",
            "strict": True,
            "parameters": {
                "type": "object",
                "required": ["switch_to", "justification", "thinking_level"],
                "properties": {
                    "switch_to": {
                        "enum": ["thinker"],
                        "type": "string",
                        "description": "The persona to switch to",
                    },
                    "justification": {
                        "type": "string",
                        "description": "Reason for switching persona",
                    },
                    "thinking_level": {
                        "enum": ["high", "medium", "low"],
                        "type": "string",
                        "description": "Amount of thinking done by the thinker persona",
                    },
                },
                "additionalProperties": False,
            },
            "description": "Ability to switch personas in the middle of the conversation",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "google_search",
            "strict": True,
            "parameters": {
                "type": "object",
                "required": ["q"],
                "properties": {
                    "q": {"type": "string", "description": "The search query string."}
                },
                "additionalProperties": False,
            },
            "description": "Performs a Google search with the specified query and returns results.",
        },
    },
    # ------------------------------
    # Scratchpad Tools
    # ------------------------------
    {
        "type": "function",
        "function": {
            "name": "scratchpad_create_entry",
            "description": "Create or append a note in the agent’s scratchpad. MLA citations encouraged.",
            "parameters": {
                "type": "object",
                "required": ["title", "content"],
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short descriptive title for the scratchpad entry.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Note content (text). Include MLA citations if referencing external sources.",
                    },
                },
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scratchpad_delete_entry",
            "description": "Deletes a note/block from the scratchpad by ID number.",
            "parameters": {
                "type": "object",
                "required": ["entry_id"],
                "properties": {
                    "entry_id": {
                        "type": "integer",
                        "description": "Scratchpad note ID to delete",
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
            "name": "scratchpad_replace_entry",
            "description": "Replaces the content of a scratchpad note by ID.",
            "parameters": {
                "type": "object",
                "required": ["entry_id", "content"],
                "properties": {
                    "entry_id": {
                        "type": "integer",
                        "description": "Scratchpad note ID to modify",
                    },
                    "content": {
                        "type": "string",
                        "description": "New content. Use MLA style citations if referencing external data.",
                    },
                },
                "additionalProperties": False,
            },
            "strict": True,
        },
    },
]

# Tools that EXCLUDE scratchpad calls
TOOLS_NO_SCRATCHPAD = [
    {
        "type": "function",
        "function": {
            "name": "scrape_urls",
            "strict": True,
            "parameters": {
                "type": "object",
                "required": ["urls", "use_cache"],
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "A single URL of a webpage",
                        },
                        "description": "An array of string URLs of the webpages to scrape",
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "Flag to indicate whether to use cached data",
                    },
                },
                "additionalProperties": False,
            },
            "description": "Scrapes a webpage and returns its markdown equivalent",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "switch_personas",
            "strict": True,
            "parameters": {
                "type": "object",
                "required": ["switch_to", "justification", "thinking_level"],
                "properties": {
                    "switch_to": {
                        "enum": ["thinker"],
                        "type": "string",
                        "description": "The persona to switch to",
                    },
                    "justification": {
                        "type": "string",
                        "description": "Reason for switching persona",
                    },
                    "thinking_level": {
                        "enum": ["high", "medium", "low"],
                        "type": "string",
                        "description": "Amount of thinking done by the thinker persona",
                    },
                },
                "additionalProperties": False,
            },
            "description": "Ability to switch personas in the middle of the conversation",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "google_search",
            "strict": True,
            "parameters": {
                "type": "object",
                "required": ["q"],
                "properties": {
                    "q": {"type": "string", "description": "The search query string."}
                },
                "additionalProperties": False,
            },
            "description": "Performs a Google search with the specified query and returns results.",
        },
    },
]


def stream_message(
    messages,
    model="gpt-4o",
    temperature=0.06,
    max_tokens=16000,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
    use_scratchpad=True,
):
    """
    Streams the chat-completion with or without scratchpad tools.
    """
    chosen_tools = TOOLS_WITH_SCRATCHPAD if use_scratchpad else TOOLS_NO_SCRATCHPAD

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        stream=True,
        tools=chosen_tools,
    )
    for chunk in response:
        yield chunk
