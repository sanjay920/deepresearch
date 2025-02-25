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
When you don't know something, admit it rather than making up information."""
