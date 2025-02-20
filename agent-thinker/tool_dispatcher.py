import json
from tools.scrape_urls import scrape_urls_call
from tools.google_search import google_search_call

# Mapping of tool names to their corresponding call implementations.
TOOL_MAP = {
    "scrape_urls": scrape_urls_call,
    "google_search": google_search_call,
}


def dispatch_tool_call(tool_call):
    """
    Dispatches a tool call request to its corresponding implementation.

    The tool_call should include a 'function' key with:
      - name: the tool's name (e.g., "scrape_urls")
      - arguments: a JSON string or dict of the parameters
    """
    func_info = tool_call.get("function", {})
    name = func_info.get("name")
    arguments = func_info.get("arguments", "{}")
    try:
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
    except Exception as e:
        raise ValueError(f"Invalid JSON for arguments: {e}")

    if name in TOOL_MAP:
        return TOOL_MAP[name](**arguments)
    else:
        raise NotImplementedError(f"Tool {name} is not implemented")
