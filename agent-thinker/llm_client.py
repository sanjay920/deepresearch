import os
from openai import OpenAI

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define the available tools
TOOLS = [
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
                        "description": "Flag to indicate whether to use cached data (default is true). Set to false when fetching a webpage with live info such as espn.com/nba/scoreboard or anything with dynamic content",
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
                        "description": "The persona to switch to. Thinker helps the assistant plan out and synthesize information",
                    },
                    "justification": {
                        "type": "string",
                        "description": "Reason for why the assistant has decided to take a pause and think",
                    },
                    "thinking_level": {
                        "enum": ["high", "medium", "low"],
                        "type": "string",
                        "description": "Amount of thinking the subconscience will do. High will make the user wait longer but think better.",
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


def send_message(
    messages,
    model="gpt-4o",
    temperature=0.06,
    max_tokens=16000,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
):
    """
    Sends a blocking chat-completion request to the LLM using the latest OpenAI SDK interface.

    Args:
        messages (list): The conversation history to send.
        model (str): Model name to use.
        temperature (float): Sampling temperature.
        max_tokens (int): Maximum token count for the response.
        top_p (float): Top probability for nucleus sampling.
        frequency_penalty (float): Frequency penalty.
        presence_penalty (float): Presence penalty.

    Returns:
        dict: The complete response from the chat-completion API.
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        tools=TOOLS,
    )
    return response


def stream_message(
    messages,
    model="gpt-4o",
    temperature=0.06,
    max_tokens=16000,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
):
    """
    Streams the chat-completion response from the LLM using the latest OpenAI SDK interface.

    This generator yields each delta chunk as it arrives.

    Args:
        messages (list): The conversation history to send.
        model (str): Model name to use.
        temperature (float): Sampling temperature.
        max_tokens (int): Maximum token count for the response.
        top_p (float): Top probability for nucleus sampling.
        frequency_penalty (float): Frequency penalty.
        presence_penalty (float): Presence penalty.

    Yields:
        dict: Each chunk of the streamed response.
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        stream=True,
        tools=TOOLS,
    )
    for chunk in response:
        yield chunk
