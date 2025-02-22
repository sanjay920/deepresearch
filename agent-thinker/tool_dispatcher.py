import json
from tools.scrape_urls import scrape_urls_call
from tools.google_search import google_search_call
from tools.switch_personas import switch_personas_call


# ---------------------------
# Scratchpad Functions
# ---------------------------
def scratchpad_create_entry(title, content, scratchpad_state):
    """
    Creates a new note/block in the scratchpad_state dictionary.
    """
    entry_id = len(scratchpad_state) + 1
    scratchpad_state[entry_id] = {"title": title, "content": content}
    return f"Created new scratchpad entry #{entry_id} with title '{title}'."


def scratchpad_delete_entry(entry_id, scratchpad_state):
    """
    Deletes a note/block by ID from the scratchpad_state dictionary.
    """
    if entry_id not in scratchpad_state:
        return f"Error: entry_id '{entry_id}' not found."
    del scratchpad_state[entry_id]
    return f"Deleted scratchpad entry #{entry_id}."


def scratchpad_replace_entry(entry_id, content, scratchpad_state):
    """
    Replaces or updates the content of a note (block), identified by ID.
    """
    if entry_id not in scratchpad_state:
        return f"Error: entry_id '{entry_id}' not found."
    scratchpad_state[entry_id]["content"] = content
    return f"Updated scratchpad entry #{entry_id}."


# ---------------------------
# Legacy tools
# ---------------------------
TOOL_MAP = {
    "scrape_urls": scrape_urls_call,
    "google_search": google_search_call,
    "switch_personas": switch_personas_call,
}


def dispatch_tool_call(
    tool_call, conversation=None, thinking_level=None, scratchpad_state=None
):
    """
    Main dispatcher for tool calls. We route scratchpad calls or fallback to TOOL_MAP.
    """
    function_name = tool_call["function"]["name"]
    arguments = tool_call["function"]["arguments"]

    # Scratchpad calls:
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

    # Otherwise fallback to known tools
    if function_name not in TOOL_MAP:
        raise ValueError(f"Unknown tool: {function_name}")

    handler = TOOL_MAP[function_name]

    # special case for switch_personas
    if function_name == "switch_personas":
        return handler(
            switch_to=arguments["switch_to"],
            conversation=conversation,
            thinking_level=thinking_level or "high",
        )

    # normal call
    return handler(**arguments)
