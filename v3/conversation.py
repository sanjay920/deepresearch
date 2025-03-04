import logging
import json


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
                    f"Tool call detected - Name: {tool_name}, "
                    f"Parameters: {tool_input}"
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
            result: The result of the tool execution (string or dict)
        """
        logging.info(f"Adding tool result for tool ID: {tool_id}")
        logging.info(f"Result type: {type(result).__name__}")

        # Get the last assistant message to preserve thinking blocks
        last_assistant_message = None
        for message in reversed(self.messages):
            if message["role"] == "assistant":
                last_assistant_message = message
                break

        logging.info(
            f"Found last assistant message: {last_assistant_message is not None}"
        )

        # Extract thinking blocks from the last assistant message
        thinking_blocks = []
        if last_assistant_message:
            for block in last_assistant_message.get("content", []):
                if block["type"] in ["thinking", "redacted_thinking"]:
                    thinking_blocks.append(block)

            logging.info(f"Extracted {len(thinking_blocks)} thinking blocks")

        # Create a new user message with tool results and preserved thinking blocks
        # Only include thinking blocks if there are any
        content_blocks = []
        if thinking_blocks:
            content_blocks.extend(thinking_blocks)
            logging.info(f"Added {len(thinking_blocks)} thinking blocks to content")

        # Ensure result is a string
        try:
            if isinstance(result, dict):
                logging.info("Converting dict result to JSON string")
                result_str = json.dumps(result)
            elif not isinstance(result, str):
                logging.info(f"Converting {type(result).__name__} result to string")
                result_str = str(result)
            else:
                logging.info("Result is already a string, using as is")
                result_str = result

            logging.debug(
                f"Final result string (first 100 chars): {result_str[:100]}..."
            )
        except Exception as e:
            logging.error(f"Error converting result to string: {str(e)}")
            logging.error(f"Exception type: {type(e).__name__}")
            # Provide a fallback
            result_str = json.dumps({"error": f"Failed to convert result: {str(e)}"})
            logging.info("Using fallback error result")

        content_blocks.append(
            {"type": "tool_result", "tool_use_id": tool_id, "content": result_str}
        )
        logging.info(f"Created tool result content block for tool ID: {tool_id}")

        tool_result_message = {
            "role": "user",
            "content": content_blocks,
        }

        self.messages.append(tool_result_message)
        logging.info("Added tool result message to conversation history")

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

    def save_to_disk(self, filepath: str):
        """Save the entire conversation to a JSON file."""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.messages, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving conversation to {filepath}: {str(e)}")

    def load_from_disk(self, filepath: str):
        """Load conversation from a JSON file (overwrites current messages)."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.messages = json.load(f)
        except Exception as e:
            logging.error(f"Error loading conversation from {filepath}: {str(e)}")
