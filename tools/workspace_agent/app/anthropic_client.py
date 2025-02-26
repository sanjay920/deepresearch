import os
import logging
from typing import Dict, Any, List, Optional
import json

import anthropic
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class AnthropicClient:
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-3-7-sonnet-20250219"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(
            exception_types=(anthropic.RateLimitError, anthropic.APIError)
        ),
    )
    def generate_with_tools(
        self, prompt: str, system_instruction: str, tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate content with tool use capability."""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.2,
                system=system_instruction,
                messages=[{"role": "user", "content": prompt}],
                tools=tools,
            )

            tool_calls = []
            text_content = ""

            for content_block in response.content:
                if content_block.type == "text":
                    text_content = content_block.text
                elif content_block.type == "tool_use":
                    tool_calls.append(
                        {
                            "name": content_block.name,
                            "input": content_block.input,
                            "id": content_block.id,
                        }
                    )

            return {
                "text": text_content,
                "tool_calls": tool_calls,
            }

        except anthropic.RateLimitError as e:
            logger.error(f"Anthropic rate limit exceeded: {str(e)}")
            raise
        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Anthropic: {str(e)}")
            raise
