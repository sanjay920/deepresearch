import json
from tools.scrape_urls import scrape_urls_call
from tools.google_search import google_search_call
from tools.switch_personas import switch_personas_call

# Mapping of tool names to their corresponding call implementations.
TOOL_MAP = {
    "scrape_urls": scrape_urls_call,
    "google_search": google_search_call,
    "switch_personas": switch_personas_call,
}


def dispatch_tool_call(tool_call, conversation=None, thinking_level=None):
    """Dispatches a tool call to the appropriate handler function.

    Args:
        tool_call (dict): The tool call object containing function name and arguments
        conversation (Conversation, optional): The current conversation context
        thinking_level (str, optional): The reasoning effort level for thinking operations

    Returns:
        str: The result of the tool call
    """
    function_name = tool_call["function"]["name"]
    arguments = tool_call["function"]["arguments"]

    if function_name not in TOOL_MAP:
        raise ValueError(f"Unknown tool: {function_name}")

    handler = TOOL_MAP[function_name]

    # Special handling for switch_personas which needs additional context
    if function_name == "switch_personas":
        return handler(
            switch_to=arguments["switch_to"],
            conversation=conversation,
            thinking_level=thinking_level or "high",
        )

    # Normal tool call handling
    return handler(**arguments)
