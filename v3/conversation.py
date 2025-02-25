from typing import List, Dict, Any, Optional
import logging


class Conversation:
    """Conversation history manager with tool call support."""

    def __init__(self):
        self.messages = []

    def add_user_message(self, content: str):
        """Add a user message to the conversation."""
        # Directly add the user message without any timestamp processing
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content_blocks):
        """
        Add an assistant message to the conversation history.

        Args:
            content_blocks: List of content blocks from the assistant
        """
        # Extract text content and tool use from content blocks
        message = {"role": "assistant", "content": []}

        # Add each content block directly to the message content
        for block in content_blocks:
            if block["type"] == "text":
                message["content"].append(
                    {"type": "text", "text": block.get("text", "")}
                )
            elif block["type"] == "tool_use":
                # Log tool use details for debugging
                tool_name = block.get("name", "unknown_tool")
                tool_input = block.get("input", {})
                logging.debug(
                    f"Tool call detected - Name: {tool_name}, Parameters: {tool_input}"
                )

                message["content"].append(
                    {
                        "type": "tool_use",
                        "id": block.get("id"),
                        "name": block.get("name"),
                        "input": block.get("input"),
                    }
                )

        self.messages.append(message)

    def add_tool_result(self, tool_id, result):
        """
        Add a tool result to the conversation.

        Args:
            tool_id: The ID of the tool that was called
            result: The result of the tool execution
        """
        # Get the last assistant message to preserve thinking blocks
        last_assistant_message = None
        for message in reversed(self.messages):
            if message["role"] == "assistant":
                last_assistant_message = message
                break

        # Extract thinking blocks from the last assistant message
        thinking_blocks = []
        if last_assistant_message:
            for block in last_assistant_message.get("content", []):
                if block["type"] in ["thinking", "redacted_thinking"]:
                    thinking_blocks.append(block)

        # Create a new user message with tool results and preserved thinking blocks
        # Only include thinking blocks if there are any (i.e., if this is a tool use turn)
        content_blocks = []
        if thinking_blocks:
            content_blocks.extend(thinking_blocks)

        content_blocks.append(
            {"type": "tool_result", "tool_use_id": tool_id, "content": result}
        )

        tool_result_message = {
            "role": "user",
            "content": content_blocks,
        }

        self.messages.append(tool_result_message)

    def get_messages(self):
        """Get all messages in the conversation."""
        return self.messages

    def clear(self):
        """Clear the conversation history."""
        self.messages = []

    def is_first_turn(self):
        """Check if this is the first conversation turn."""
        return getattr(self, "_first_turn", True)

    def mark_not_first_turn(self):
        """Mark that we're no longer in the first conversation turn."""
        self._first_turn = False

    def get_visible_messages(self):
        """Get messages without thinking blocks for token counting."""
        visible_messages = []
        for message in self.messages:
            if message["role"] == "user":
                # User messages are kept as is
                visible_messages.append(message)
            elif message["role"] == "assistant":
                # For assistant messages, filter out thinking blocks
                visible_content = []
                for block in message.get("content", []):
                    if block["type"] not in ["thinking", "redacted_thinking"]:
                        visible_content.append(block)

                if visible_content:
                    visible_messages.append(
                        {"role": "assistant", "content": visible_content}
                    )

        return visible_messages
