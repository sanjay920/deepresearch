class Conversation:
    """A simple in-memory conversation history manager."""

    def __init__(self):
        self.history = []

    def add_message(self, message):
        self.history.append(message)

    def get_history(self):
        return self.history

    def format_conversation(self):
        """
        Formats the conversation history into a string format suitable for the thinker persona.
        """
        formatted = []
        for msg in self.history:
            role = msg.get("role", "")

            if role == "assistant" and msg.get("tool_calls"):
                # Format tool calls
                tool_calls = []
                for call in msg["tool_calls"]:
                    tool_name = call["function"]["name"]
                    tool_calls.append(f"[Tool Call] {tool_name}")
                formatted.append(f"assistant: {' '.join(tool_calls)}")

            elif role == "tool":
                # Format tool responses
                content = msg.get("content", [{}])[0].get("text", "")
                formatted.append(f"tool: {content}")

            elif role == "user":
                # Format user messages
                content = msg.get("content", [{}])[0].get("text", "")
                formatted.append(f"user: {content}")

            elif role == "assistant" and msg.get("content"):
                # Format assistant responses
                content = msg.get("content", [{}])[0].get("text", "")
                formatted.append(f"assistant: {content}")

        return "\n\n".join(formatted)
