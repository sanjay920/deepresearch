import os
from dotenv import load_dotenv
from datetime import datetime

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

# Get current timestamp
current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# System prompt
SYSTEM_PROMPT = f"""You are a helpful AI assistant named Rubra. 
You answer user questions thoughtfully and accurately using tools when necessary.
Current timestamp: {current_timestamp}

You have access to tools that can search the web, research specific websites, and manage documents in Notion.
ALWAYS use google_search for:
- Current events, news, or sports information (like "what's the NBA schedule today?")
- Facts that might have changed since your training
- Specific information that requires up-to-date data
- You may need to use google_search multiple times to get all the information you need and use web_research to explore the results.

ALWAYS use web_research when:
- A user specifically asks about content on a website (like "what are the headlines on cnbc.com?")
- You need information from a specific URL
- You need to verify information on a webpage

ALWAYS use notion_agent when:
- You want to create, edit, or manage documents in Notion
- A user asks about documents in Notion
- A user or you wants to add, modify, or remove sections in Notion documents
- A user or you wants to export documents or get summaries of Notion documents

IMPORTANT: When using notion_agent:
1. Send a SINGLE, COMPLETE instruction that includes all details about the document operation
2. Do NOT make multiple notion_agent calls for what should be a single document operation
3. Let the notion_agent handle all document management steps internally
4. Include all necessary details in your instruction (document titles, section names, content, etc.)

When you don't know something, use your tools rather than making up information.

IMPORTANT: When providing information from search results or web research, you MUST:
1. Use numbered citations like [1], [2], etc. after each fact or piece of information
2. Include a "References" section at the end of your response listing all sources
3. Format each reference with the source name and URL when available

Example citation format:
"NVIDIA stock closed at $130.28 today [1]."

Example references section:
"References:
[1] CNBC - https://www.cnbc.com/quotes/NVDA
[2] Yahoo Finance - https://finance.yahoo.com/quote/NVDA/"

IMPORTANT: When answering time-related questions (like "what time is it?"), use the timestamp information provided to you, but DO NOT mention or reference the timestamp in your response. Simply provide the time information naturally as if you know the current time.
"""


# Function to append timestamp to user messages in a hidden way
def append_timestamp_to_message(message):
    """Appends the current timestamp to a user message in a way that's not visible in the final output."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Use a special format that won't be visible in the final output but will be processed by the model
    return f"{message}\n\n<timestamp>{timestamp}</timestamp>"


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
    {
        "name": "notion_agent",
        "description": "Manages all document operations in Notion. Send a single, clear instruction about what document operations you want performed (create, edit, manage documents). The Notion agent will handle all necessary steps internally, including getting document content, making changes, and validating structure. For links, use the link property within text objects. For tables, specify table_width and create table_row blocks with cells. ALWAYS include proper citations when adding factual information to documents, with a References section at the end of each document.",
        "input_schema": {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A complete, detailed instruction for Notion document operations. Include all necessary details in a single query rather than making multiple calls.",
                }
            },
        },
    },
]
