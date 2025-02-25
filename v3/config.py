import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration settings
CONFIG = {
    "model": "claude-3-7-sonnet-20250219",
    "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY"),
    "max_tokens": 20000,
    "temperature": 1.0,
    # Extended thinking configuration
    "thinking": {
        "enabled": True,
        "budget_tokens": 16000,
    },
}

# System prompt
SYSTEM_PROMPT = """You are a helpful, harmless, and honest AI assistant. 
You answer user questions thoughtfully and accurately.

You have access to tools that can search the web and research specific websites.
ALWAYS use google_search for:
- Current events, news, or sports information (like "what's the NBA schedule today?")
- Facts that might have changed since your training
- Specific information that requires up-to-date data
- You may need to use google_search multiple times to get all the information you need and use web_research to explore the results.

ALWAYS use web_research when:
- A user specifically asks about content on a website (like "what are the headlines on cnbc.com?")
- You need information from a specific URL
- You need to verify information on a webpage

When you don't know something, use your tools rather than making up information."""

# Tool definitions
TOOLS = [
    {
        "name": "google_search",
        "description": "Performs a Google search with the specified query and returns results.",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string. Dont use too many terms.",
                }
            },
        },
    },
    {
        "name": "web_research",
        "description": "Researches a specific webpage to answer a question",
        "input_schema": {
            "type": "object",
            "required": ["url", "query"],
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the webpage to research.",
                },
                "query": {
                    "type": "string",
                    "description": "The specific question to answer from the webpage.",
                },
            },
        },
    },
]
