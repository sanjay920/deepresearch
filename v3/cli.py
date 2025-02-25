#!/usr/bin/env python3
import anthropic
import sys
import logging
import time
import threading
import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from conversation import Conversation
from config import CONFIG, SYSTEM_PROMPT, TOOLS
from tools import google_search, web_research
from rich.spinner import Spinner
from rich.live import Live
import tiktoken

# Setup console and logging
console = Console()
logging.basicConfig(
    level=logging.INFO,  # Changed to INFO to see tool execution logs
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("claude_cli.log")
    ],  # Send logs to a file instead of stdout
)


# Initialize tiktoken encoder for token counting
def get_encoder():
    """Get the appropriate tiktoken encoder based on the model."""
    model = CONFIG["model"]
    try:
        if "claude" in model.lower():
            # For Claude models, use cl100k_base which is close to Claude's tokenizer
            return tiktoken.get_encoding("cl100k_base")
        else:
            # Try to get model-specific encoding, fallback to cl100k_base
            return tiktoken.encoding_for_model(model)
    except:
        # Fallback to cl100k_base if specific encoding not found
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text):
    """Count the number of tokens in a text string."""
    encoder = get_encoder()
    return len(encoder.encode(text))


def execute_tool_call(tool_call):
    """
    Execute a tool call based on its name and input.

    Args:
        tool_call: Dictionary with tool details and input

    Returns:
        The result of the tool execution
    """
    tool_name = tool_call["name"]
    tool_input = tool_call["input"]

    console.print(f"[bold yellow]Executing tool:[/bold yellow] {tool_name}")

    try:
        if tool_name == "google_search":
            query = tool_input.get("query", tool_input.get("q", ""))
            if not query:
                console.print("[bold red]Error:[/bold red] Empty search query")
                return {"error": "Empty search query"}

            console.print(f"[dim]Searching for:[/dim] {query}")
            return google_search(query)

        elif tool_name == "web_research":
            url = tool_input.get("url", "")
            query = tool_input.get("query", "")
            console.print(f"[dim]Researching:[/dim] {query} [dim]on[/dim] {url}")
            return web_research(url, query)

        else:
            error_msg = f"Unknown tool: {tool_name}"
            logging.error(error_msg)
            return {"error": error_msg}

    except Exception as e:
        error_msg = f"Tool execution error: {str(e)}"
        logging.error(error_msg)
        return {"error": error_msg}


def main():
    """Main CLI interface for conversing with Claude and displaying thinking."""
    console.print(
        Panel.fit(
            "[bold blue]Deep Search[/bold blue]",
            title="Welcome",
        )
    )
    console.print("Type your messages or [blue]'exit'[/blue] to quit")
    console.print(
        "Commands: [blue]thinking:on[/blue], [blue]thinking:off[/blue], "
        "[blue]clear[/blue]"
    )

    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=CONFIG["anthropic_api_key"])
    conversation = Conversation()
    show_thinking = True  # Default to showing thinking

    while True:
        user_input = console.input("\n[bold green]You:[/bold green] ")

        # Command handling
        if user_input.lower() in ["exit", "quit"]:
            console.print("[bold blue]Goodbye![/bold blue]")
            break

        if user_input.lower() == "thinking:on":
            show_thinking = True
            console.print("[bold blue]Thinking display turned ON[/bold blue]")
            continue

        elif user_input.lower() == "thinking:off":
            show_thinking = False
            console.print("[bold blue]Thinking display turned OFF[/bold blue]")
            continue

        elif user_input.lower() == "clear":
            conversation.clear()
            console.print("[bold blue]Conversation history cleared[/bold blue]")
            continue

        # Count tokens in user message
        user_tokens = count_tokens(user_input)
        console.print(f"[cyan][User message tokens: {user_tokens}][/cyan]")

        # Add user message to conversation without timestamp
        conversation.add_user_message(user_input)

        # Show a simple "message received" notice
        console.print("[bold yellow]Message Received[/bold yellow]")

        # Process streaming conversation with tool calls
        process_conversation(client, conversation, show_thinking)


def process_conversation(client, conversation, show_thinking):
    """
    Process a complete conversation turn, handling thinking and tools.

    Args:
        client: Anthropic client
        conversation: Conversation history manager
        show_thinking: Whether to display thinking blocks
    """
    # Initialize tracking variables
    all_content_blocks = []
    thinking_start_time = None
    thinking_started = False
    response_started = False
    tool_calls = []
    is_tool_use = False
    assistant_response_text = ""  # Track assistant's text response for token counting

    # Get the user's message token count from the last message
    last_user_message = None
    for message in reversed(conversation.get_messages()):
        if message["role"] == "user":
            last_user_message = message["content"]
            break

    user_tokens = count_tokens(last_user_message) if last_user_message else 0

    # Add a variable to track partial JSON for tool inputs
    tool_input_json_parts = {}

    try:
        # Create a spinner to show while waiting for the first response
        spinner = Spinner("dots", text="Waiting for assistant...")

        # Get current timestamp for this request
        current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # Create a timestamped system prompt
        timestamped_system_prompt = (
            f"{SYSTEM_PROMPT}\n\nCurrent time: {current_timestamp}"
        )

        # Start the spinner in a Live context
        with Live(spinner, refresh_per_second=10, transient=True) as live:
            # Stream the response from Claude
            with client.messages.stream(
                model=CONFIG["model"],
                max_tokens=CONFIG["max_tokens"],
                system=timestamped_system_prompt,  # Use timestamped system prompt
                messages=conversation.get_messages(),
                temperature=CONFIG["temperature"],
                thinking={
                    "type": "enabled",
                    "budget_tokens": CONFIG["thinking"]["budget_tokens"],
                },
                tools=TOOLS,
            ) as stream:
                # Track content blocks for conversation history
                current_block = None

                for event in stream:
                    # Stop the spinner on first event
                    if live.is_started:
                        live.stop()

                    if event.type == "content_block_start":
                        block_type = event.content_block.type
                        current_block = {"type": block_type}

                        if block_type == "thinking":
                            current_block["thinking"] = ""
                            if show_thinking and not thinking_started:
                                thinking_start_time = time.time()
                                console.print("\n[bold blue]Thinking...[/bold blue]")
                                thinking_started = True

                        elif block_type == "redacted_thinking":
                            current_block["data"] = ""
                            if show_thinking and not thinking_started:
                                console.print(
                                    "\n[bold red]Redacted Thinking:[/bold red]"
                                )
                                console.print(
                                    "[red]Some thinking content was filtered for safety[/red]"
                                )
                                thinking_start_time = time.time()
                                thinking_started = True

                        elif block_type == "text":
                            current_block["text"] = ""
                            if not response_started:
                                # Show thinking time if applicable
                                if thinking_start_time:
                                    elapsed = time.time() - thinking_start_time
                                    minutes, seconds = divmod(int(elapsed), 60)
                                    console.print(
                                        f"\n[bold yellow]Thinking completed in {minutes:02d}:{seconds:02d}[/bold yellow]"
                                    )

                                # Add a separator between thinking and response
                                if show_thinking and thinking_started:
                                    console.print("\n" + "-" * 80 + "\n")
                                console.print("\n[bold green]Assistant:[/bold green]")
                                response_started = True

                        elif block_type == "tool_use":
                            is_tool_use = True
                            current_block["id"] = event.content_block.id
                            current_block["name"] = event.content_block.name
                            current_block["input"] = event.content_block.input

                            # More detailed logging to understand the structure
                            logging.info(
                                f"Tool call detected: {event.content_block.name}"
                            )
                            logging.info(f"Tool call ID: {event.content_block.id}")
                            logging.info(
                                f"Tool call input: {event.content_block.input}"
                            )
                            logging.info(f"Full content block: {event.content_block}")

                            # Only add to tool_calls if we have input parameters
                            if event.content_block.input:
                                tool_calls.append(
                                    {
                                        "id": event.content_block.id,
                                        "name": event.content_block.name,
                                        "input": event.content_block.input,
                                    }
                                )
                            else:
                                # If input is empty, wait for potential updates in content_block_delta events
                                logging.warning(
                                    f"Empty input for tool {event.content_block.name}. Will wait for updates."
                                )

                            # Show tool use in console
                            if not response_started:
                                if thinking_start_time:
                                    elapsed = time.time() - thinking_start_time
                                    minutes, seconds = divmod(int(elapsed), 60)
                                    console.print(
                                        f"\n[bold yellow]Thinking completed in {minutes:02d}:{seconds:02d}[/bold yellow]"
                                    )

                                if show_thinking and thinking_started:
                                    console.print("\n" + "-" * 80 + "\n")
                                console.print("\n[bold green]Assistant:[/bold green]")
                                response_started = True

                            console.print(
                                f"\n[bold magenta]Using tool:[/bold magenta] {event.content_block.name}"
                            )

                    elif event.type == "content_block_delta":
                        delta_type = event.delta.type

                        # Log all delta types to understand what's coming through
                        logging.info(f"Delta type: {delta_type}")
                        logging.info(f"Delta content: {event.delta}")

                        if delta_type == "thinking_delta":
                            current_block["thinking"] += event.delta.thinking
                            if show_thinking:
                                console.print(
                                    event.delta.thinking, end="", highlight=False
                                )
                                sys.stdout.flush()

                        elif delta_type == "text_delta":
                            current_block["text"] += event.delta.text
                            assistant_response_text += (
                                event.delta.text
                            )  # Track for token counting
                            console.print(event.delta.text, end="", highlight=False)
                            sys.stdout.flush()

                        elif delta_type == "input_json_delta":
                            # Handle partial JSON for tool inputs
                            if current_block and current_block["type"] == "tool_use":
                                tool_id = current_block.get("id")
                                if tool_id not in tool_input_json_parts:
                                    tool_input_json_parts[tool_id] = ""

                                # Append the partial JSON
                                if hasattr(event.delta, "partial_json"):
                                    tool_input_json_parts[
                                        tool_id
                                    ] += event.delta.partial_json

                                    # Try to parse the JSON if it looks complete
                                    json_str = tool_input_json_parts[tool_id]
                                    if json_str and (
                                        json_str.startswith("{")
                                        and json_str.endswith("}")
                                    ):
                                        try:
                                            # Parse the complete JSON
                                            input_params = json.loads(json_str)
                                            logging.info(
                                                f"Parsed tool input: {input_params}"
                                            )

                                            # Update the current block
                                            current_block["input"] = input_params

                                            # Update or add to tool_calls
                                            tool_call_exists = False
                                            for tool_call in tool_calls:
                                                if tool_call["id"] == tool_id:
                                                    tool_call["input"] = input_params
                                                    tool_call_exists = True
                                                    break

                                            if not tool_call_exists:
                                                tool_calls.append(
                                                    {
                                                        "id": tool_id,
                                                        "name": current_block["name"],
                                                        "input": input_params,
                                                    }
                                                )

                                        except json.JSONDecodeError:
                                            # JSON is not complete yet, continue collecting
                                            logging.info(
                                                f"Partial JSON not yet complete: {json_str}"
                                            )

                        elif delta_type == "signature_delta":
                            current_block["signature"] = event.delta.signature

                    elif event.type == "content_block_stop":
                        if current_block:
                            all_content_blocks.append(current_block)
                            current_block = None
                            # Add a newline after each content block
                            console.print()

                # Add assistant's response to conversation history
                conversation.add_assistant_message(all_content_blocks)

                # Count tokens in assistant's response
                assistant_tokens = count_tokens(assistant_response_text)

                # Count tokens in visible conversation (excluding thinking blocks)
                if hasattr(conversation, "get_visible_messages"):
                    visible_conversation_text = json.dumps(
                        conversation.get_visible_messages()
                    )
                    visible_conversation_tokens = count_tokens(
                        visible_conversation_text
                    )
                    overhead_tokens = (
                        visible_conversation_tokens - user_tokens - assistant_tokens
                    )
                    total_tokens = user_tokens + assistant_tokens + overhead_tokens
                else:
                    # Count tokens in entire conversation
                    conversation_text = json.dumps(conversation.get_messages())
                    conversation_tokens = count_tokens(conversation_text)
                    overhead_tokens = (
                        conversation_tokens - user_tokens - assistant_tokens
                    )
                    total_tokens = user_tokens + assistant_tokens + overhead_tokens

                # Display the total and breakdown
                console.print(
                    f"\n[cyan][Tokens: {total_tokens} total = {user_tokens} (user) + {assistant_tokens} (assistant) + {overhead_tokens} (overhead)][/cyan]"
                )

                # Display token usage if available
                if hasattr(stream, "usage") and stream.usage:
                    input_tokens = stream.usage.input_tokens
                    output_tokens = stream.usage.output_tokens
                    console.print(
                        f"[dim]API usage: {input_tokens} input, {output_tokens} output[/dim]"
                    )

        # Handle tool calls if any
        if is_tool_use:
            console.print("\n[bold yellow]Executing tools...[/bold yellow]")

            # Execute each tool call and add results to conversation
            for tool_call in tool_calls:
                result = execute_tool_call(tool_call)
                result_str = json.dumps(result)

                # FIXED: Only add the tool result without thinking blocks
                conversation.add_tool_result(tool_call["id"], result_str)
                console.print(f"[dim]Tool result added to conversation[/dim]")

            # Continue the conversation with new information
            console.print(
                "\n[bold yellow]Continuing with tool results...[/bold yellow]"
            )

            # IMPORTANT: Disable thinking for the tool result response
            # This is the key fix - we need to disable thinking when continuing after tool results
            process_conversation_without_thinking(client, conversation, show_thinking)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        logging.error(f"API error: {str(e)}")


def process_conversation_without_thinking(client, conversation, show_thinking):
    """
    Process a conversation turn after tool results without using thinking.

    Args:
        client: Anthropic client
        conversation: Conversation history manager
        show_thinking: Whether to display thinking (not used in this function)
    """
    try:
        # Create a spinner to show while waiting for the first response
        spinner = Spinner("dots", text="Processing tool results...")
        assistant_response_text = (
            ""  # Track assistant's text response for token counting
        )

        # Get current timestamp for this request
        current_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # Create a timestamped system prompt
        timestamped_system_prompt = (
            f"{SYSTEM_PROMPT}\n\nCurrent time: {current_timestamp}"
        )

        # Start the spinner in a Live context
        with Live(spinner, refresh_per_second=10, transient=True) as live:
            # Stream the response from Claude without thinking enabled
            with client.messages.stream(
                model=CONFIG["model"],
                max_tokens=CONFIG["max_tokens"],
                system=timestamped_system_prompt,  # Use timestamped system prompt
                messages=conversation.get_messages(),
                temperature=CONFIG["temperature"],
                # No thinking parameter here
                tools=TOOLS,
            ) as stream:
                # Track content blocks for conversation history
                all_content_blocks = []
                current_block = None
                response_started = False
                tool_calls = []
                is_tool_use = False
                tool_input_json_parts = {}

                for event in stream:
                    # Stop the spinner on first event
                    if live.is_started:
                        live.stop()

                    if event.type == "content_block_start":
                        block_type = event.content_block.type
                        current_block = {"type": block_type}

                        if block_type == "text":
                            current_block["text"] = ""
                            if not response_started:
                                console.print("\n[bold green]Assistant:[/bold green]")
                                response_started = True

                        elif block_type == "tool_use":
                            is_tool_use = True
                            current_block["id"] = event.content_block.id
                            current_block["name"] = event.content_block.name
                            current_block["input"] = event.content_block.input

                            # More detailed logging to understand the structure
                            logging.info(
                                f"Tool call detected: {event.content_block.name}"
                            )
                            logging.info(f"Tool call ID: {event.content_block.id}")
                            logging.info(
                                f"Tool call input: {event.content_block.input}"
                            )
                            logging.info(f"Full content block: {event.content_block}")

                            # Only add to tool_calls if we have input parameters
                            if event.content_block.input:
                                tool_calls.append(
                                    {
                                        "id": event.content_block.id,
                                        "name": event.content_block.name,
                                        "input": event.content_block.input,
                                    }
                                )
                            else:
                                # If input is empty, wait for potential updates in content_block_delta events
                                logging.warning(
                                    f"Empty input for tool {event.content_block.name}. Will wait for updates."
                                )

                            # Show tool use in console
                            if not response_started:
                                console.print("\n[bold green]Assistant:[/bold green]")
                                response_started = True

                            console.print(
                                f"\n[bold magenta]Using tool:[/bold magenta] {event.content_block.name}"
                            )

                    elif event.type == "content_block_delta":
                        delta_type = event.delta.type

                        # Log all delta types to understand what's coming through
                        logging.info(f"Delta type: {delta_type}")
                        logging.info(f"Delta content: {event.delta}")

                        if delta_type == "text_delta":
                            current_block["text"] += event.delta.text
                            assistant_response_text += (
                                event.delta.text
                            )  # Track for token counting
                            console.print(event.delta.text, end="", highlight=False)
                            sys.stdout.flush()

                        elif delta_type == "input_json_delta":
                            # Handle partial JSON for tool inputs
                            if current_block and current_block["type"] == "tool_use":
                                tool_id = current_block.get("id")
                                if tool_id not in tool_input_json_parts:
                                    tool_input_json_parts[tool_id] = ""

                                # Append the partial JSON
                                if hasattr(event.delta, "partial_json"):
                                    tool_input_json_parts[
                                        tool_id
                                    ] += event.delta.partial_json

                                    # Try to parse the JSON if it looks complete
                                    json_str = tool_input_json_parts[tool_id]
                                    if json_str and (
                                        json_str.startswith("{")
                                        and json_str.endswith("}")
                                    ):
                                        try:
                                            # Parse the complete JSON
                                            input_params = json.loads(json_str)
                                            logging.info(
                                                f"Parsed tool input: {input_params}"
                                            )

                                            # Update the current block
                                            current_block["input"] = input_params

                                            # Update or add to tool_calls
                                            tool_call_exists = False
                                            for tool_call in tool_calls:
                                                if tool_call["id"] == tool_id:
                                                    tool_call["input"] = input_params
                                                    tool_call_exists = True
                                                    break

                                            if not tool_call_exists:
                                                tool_calls.append(
                                                    {
                                                        "id": tool_id,
                                                        "name": current_block["name"],
                                                        "input": input_params,
                                                    }
                                                )

                                        except json.JSONDecodeError:
                                            # JSON is not complete yet, continue collecting
                                            logging.info(
                                                f"Partial JSON not yet complete: {json_str}"
                                            )

                    elif event.type == "content_block_stop":
                        if current_block:
                            all_content_blocks.append(current_block)
                            current_block = None
                            # Add a newline after each content block
                            console.print()

                # Add assistant's response to conversation history
                conversation.add_assistant_message(all_content_blocks)

                # Count tokens in assistant's response
                assistant_tokens = count_tokens(assistant_response_text)

                # Get the user's message token count from the last message
                last_user_message = None
                for message in reversed(conversation.get_messages()):
                    if message["role"] == "user":
                        if isinstance(message["content"], str):
                            last_user_message = message["content"]
                            break
                        # Handle case where content is a list (tool results)
                        elif isinstance(message["content"], list):
                            for block in message["content"]:
                                if block.get("type") == "tool_result":
                                    last_user_message = block.get("content", "")
                                    break

                user_tokens = (
                    count_tokens(last_user_message) if last_user_message else 0
                )

                # Count tokens in visible conversation (excluding thinking blocks)
                if hasattr(conversation, "get_visible_messages"):
                    visible_conversation_text = json.dumps(
                        conversation.get_visible_messages()
                    )
                    visible_conversation_tokens = count_tokens(
                        visible_conversation_text
                    )
                    overhead_tokens = (
                        visible_conversation_tokens - user_tokens - assistant_tokens
                    )
                    total_tokens = user_tokens + assistant_tokens + overhead_tokens
                else:
                    # Count tokens in entire conversation
                    conversation_text = json.dumps(conversation.get_messages())
                    conversation_tokens = count_tokens(conversation_text)
                    overhead_tokens = (
                        conversation_tokens - user_tokens - assistant_tokens
                    )
                    total_tokens = user_tokens + assistant_tokens + overhead_tokens

                # Display the total and breakdown
                console.print(
                    f"\n[cyan][Tokens: {total_tokens} total = {user_tokens} (user) + {assistant_tokens} (assistant) + {overhead_tokens} (overhead)][/cyan]"
                )

                # Display token usage if available
                if hasattr(stream, "usage") and stream.usage:
                    input_tokens = stream.usage.input_tokens
                    output_tokens = stream.usage.output_tokens
                    console.print(
                        f"[dim]API usage: {input_tokens} input, {output_tokens} output[/dim]"
                    )

        # Handle tool calls if any
        if is_tool_use:
            console.print("\n[bold yellow]Executing tools...[/bold yellow]")

            # Execute each tool call and add results to conversation
            for tool_call in tool_calls:
                result = execute_tool_call(tool_call)
                result_str = json.dumps(result)
                conversation.add_tool_result(tool_call["id"], result_str)
                console.print(f"[dim]Tool result added to conversation[/dim]")

            # Continue the conversation with new information
            console.print(
                "\n[bold yellow]Continuing with tool results...[/bold yellow]"
            )
            process_conversation_without_thinking(client, conversation, show_thinking)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        logging.error(f"API error: {str(e)}")


if __name__ == "__main__":
    main()
