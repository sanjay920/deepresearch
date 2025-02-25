class Conversation:
    """Simple conversation history manager."""

    def __init__(self):
        self.messages = []

    def add_user_message(self, content: str):
        """Add a user message to the conversation."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content):
        """
        Add an assistant message to the conversation.

        Args:
            content: Could be a string or a list of content blocks
        """
        self.messages.append({"role": "assistant", "content": content})

    def get_messages(self):
        """Get all messages in the conversation."""
        return self.messages

    def clear(self):
        """Clear the conversation history."""
        self.messages = []
