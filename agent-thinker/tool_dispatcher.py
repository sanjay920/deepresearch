import json
from tools.scrape_urls import scrape_urls_call
from tools.google_search import google_search_call
from tools.switch_personas import switch_personas_call


def scratchpad_create_entry(title, content, scratchpad_state=None):
    """
    Creates a new note/block in the scratchpad_state dictionary.
    """
    if scratchpad_state is None:
        scratchpad_state = {}
    entry_id = len(scratchpad_state) + 1
    scratchpad_state[entry_id] = {"title": title, "content": content}
    return f"Created new scratchpad entry #{entry_id} with title '{title}'."


def scratchpad_delete_entry(entry_id, scratchpad_state=None):
    """
    Deletes a note/block by ID from the scratchpad_state dictionary.
    """
    if scratchpad_state is None or entry_id not in scratchpad_state:
        return f"Error: entry_id '{entry_id}' not found."
    del scratchpad_state[entry_id]
    return f"Deleted scratchpad entry #{entry_id}."


def scratchpad_replace_entry(entry_id, content, scratchpad_state=None):
    """
    Replaces or updates the content of a note (block), identified by ID.
    """
    if scratchpad_state is None or entry_id not in scratchpad_state:
        return f"Error: entry_id '{entry_id}' not found."
    scratchpad_state[entry_id]["content"] = content
    return f"Updated scratchpad entry #{entry_id}."


TOOL_MAP = {
    "scrape_urls": scrape_urls_call,
    "google_search": google_search_call,
    "switch_personas": switch_personas_call,
}


def dispatch_tool_call(
    tool_call, conversation=None, thinking_level=None, scratchpad_state=None
):
    """
    Main dispatcher for tool calls. Routes scratchpad calls or falls back to TOOL_MAP.

    Args:
        tool_call (dict): The tool call details with id and function.
        conversation (Conversation, optional): Conversation context for switch_personas.
        thinking_level (str, optional): Thinking level for switch_personas.
        scratchpad_state (dict, optional): Scratchpad state for persistence.

    Returns:
        Any: Result of the tool call execution.
    """
    function_name = tool_call["function"]["name"]
    arguments = tool_call["function"]["arguments"]

    # Handle scratchpad calls
    if function_name == "scratchpad_create_entry":
        title = arguments.get("title", "Untitled")
        content = arguments.get("content", "")
        return scratchpad_create_entry(title, content, scratchpad_state)

    elif function_name == "scratchpad_delete_entry":
        entry_id = arguments.get("entry_id", 0)
        return scratchpad_delete_entry(entry_id, scratchpad_state)

    elif function_name == "scratchpad_replace_entry":
        entry_id = arguments.get("entry_id", 0)
        new_content = arguments.get("content", "")
        return scratchpad_replace_entry(entry_id, new_content, scratchpad_state)

    # Fallback to known tools
    if function_name not in TOOL_MAP:
        raise ValueError(f"Unknown tool: {function_name}")

    handler = TOOL_MAP[function_name]

    if function_name == "switch_personas":
        return handler(
            switch_to=arguments["switch_to"],
            conversation=conversation,
            thinking_level=thinking_level or "high",
        )

    return handler(**arguments)
