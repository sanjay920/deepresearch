#!/usr/bin/env python3
import anthropic
import sys
import logging
import time
import threading
import os
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from conversation import Conversation
from config import CONFIG, SYSTEM_PROMPT

# Setup console and logging
console = Console()
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def main():
    """Main CLI interface for conversing with Claude and displaying thinking."""
    console.print(
        Panel.fit(
            "[bold blue]Claude 3.7 Sonnet with Extended Thinking[/bold blue]",
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

        # Add user message to conversation
        conversation.add_user_message(user_input)

        # Initialize content variables
        response_content = ""

        # Show a simple "thinking" message
        console.print("[bold yellow]Message Received[/bold yellow]")

        # Timer variables
        thinking_start_time = None

        try:
            # Stream the response from Claude
            with client.messages.stream(
                model=CONFIG["model"],
                max_tokens=CONFIG["max_tokens"],
                system=SYSTEM_PROMPT,
                messages=conversation.get_messages(),
                temperature=CONFIG["temperature"],
                thinking={
                    "type": "enabled",
                    "budget_tokens": CONFIG["thinking"]["budget_tokens"],
                },
            ) as stream:
                # Track content blocks for conversation history
                content_blocks = []
                current_block = None

                # Variables to track if we've started displaying thinking/response
                thinking_started = False
                response_started = False

                for event in stream:
                    if event.type == "content_block_start":
                        current_block = {"type": event.content_block.type}

                        if event.content_block.type == "thinking":
                            current_block["thinking"] = ""
                            if show_thinking and not thinking_started:
                                # Start the timer when thinking begins
                                thinking_start_time = time.time()
                                console.print("\n[bold blue]Thinking...[/bold blue]")
                                thinking_started = True

                        elif event.content_block.type == "redacted_thinking":
                            current_block["data"] = ""
                            if show_thinking and not thinking_started:
                                console.print(
                                    "\n[bold red]Redacted Thinking:[/bold red]"
                                )
                                console.print(
                                    "[red]Some thinking content was filtered "
                                    "for safety[/red]"
                                )
                                # Start the timer for redacted thinking too
                                thinking_start_time = time.time()
                                console.print("\n[bold blue]Thinking...[/bold blue]")
                                thinking_started = True

                        elif event.content_block.type == "text":
                            current_block["text"] = ""
                            if not response_started:
                                # Display final thinking time
                                if thinking_start_time:
                                    elapsed = time.time() - thinking_start_time
                                    minutes, seconds = divmod(int(elapsed), 60)
                                    console.print(
                                        f"\n[bold yellow]Thinking completed in "
                                        f"{minutes:02d}:{seconds:02d}[/bold yellow]"
                                    )

                                # Add a clear separator between thinking and response
                                if show_thinking and thinking_started:
                                    console.print("\n" + "-" * 80 + "\n")
                                console.print("\n[bold green]Assistant:[/bold green]")
                                response_started = True

                    elif event.type == "content_block_delta":
                        if event.delta.type == "thinking_delta":
                            current_block["thinking"] += event.delta.thinking
                            if show_thinking:
                                # Stream thinking content directly
                                console.print(
                                    event.delta.thinking, end="", highlight=False
                                )
                                # Ensure output is displayed immediately
                                sys.stdout.flush()

                        elif event.delta.type == "text_delta":
                            current_block["text"] += event.delta.text
                            response_content += event.delta.text
                            console.print(event.delta.text, end="", highlight=False)
                            # Ensure output is displayed immediately
                            sys.stdout.flush()

                        elif event.delta.type == "signature_delta":
                            current_block["signature"] = event.delta.signature

                    elif event.type == "content_block_stop":
                        if current_block:
                            content_blocks.append(current_block)
                            current_block = None
                            # Add a newline after each content block
                            console.print()

                # Add assistant's response to conversation history
                conversation.add_assistant_message(content_blocks)

                # Display token usage if available
                if hasattr(stream, "usage") and stream.usage:
                    input_tokens = stream.usage.input_tokens
                    output_tokens = stream.usage.output_tokens
                    console.print(
                        f"\n[dim]Token usage: {input_tokens} input, "
                        f"{output_tokens} output[/dim]"
                    )

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            logging.error(f"API error: {str(e)}")


if __name__ == "__main__":
    main()
