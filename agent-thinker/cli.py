#!/usr/bin/env python3
import os
import json
import click
from rich.console import Console
from rich.markdown import Markdown
from rich.layout import Layout
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live
from datetime import datetime

from conversation import Conversation
from llm_client import stream_message
from tool_dispatcher import dispatch_tool_call


def build_tools_panel_from_list(calls_list):
    if not calls_list:
        return Panel("No tool calls", title="Tool Calls")
    # Create a simple list of tool call names for display.
    text = "\n".join(
        [f"{i+1}. {call.function.name}" for i, call in enumerate(calls_list)]
    )
    return Panel(text, title="Tool Calls")


class ToolCallAggregator:
    """A simple aggregator for tool calls emitted in streaming responses."""

    def __init__(self):
        self.final_tool_calls = {}

    def reset(self):
        self.final_tool_calls = {}

    def process_delta(self, tool_calls):
        """Process tool call deltas from the streaming response.

        Args:
            tool_calls: A list of ChoiceDeltaToolCall objects or a single ChoiceDeltaToolCall
        """
        if not tool_calls:
            return

        # Convert single tool call to list for uniform processing
        calls = tool_calls if isinstance(tool_calls, list) else [tool_calls]

        for tool_call in calls:
            index = tool_call.index

            # Initialize if this is a new tool call
            if index not in self.final_tool_calls:
                self.final_tool_calls[index] = tool_call
                # Initialize arguments if needed
                if not hasattr(self.final_tool_calls[index].function, "arguments"):
                    self.final_tool_calls[index].function.arguments = ""

            # Accumulate arguments if present in this delta
            if hasattr(tool_call.function, "arguments"):
                current_args = self.final_tool_calls[index].function.arguments or ""
                new_args = tool_call.function.arguments or ""
                self.final_tool_calls[index].function.arguments = (
                    current_args + new_args
                )

    def get_all_calls(self):
        """Returns the list of complete tool calls."""
        return list(self.final_tool_calls.values())

    def finalize(self):
        pass


console = Console()
conversation = Conversation()


@click.command()
def chat_cli():
    # Add the system prompt message.
    system_message = {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": f"You are an assistant wearing your 'agent' hat. This means you can:  \n- Interact with tools,  \n- Reply directly to the user.\n\nIf you face a complex or multi-step request (e.g., data analysis, multi-step reasoning, or tasks that require gathering and synthesizing external information), you must switch to your 'thinker” persona. Do this by calling the 'switch_personas” function with the argument \"thinker\".\n\nWhile wearing the 'thinker” hat:  \n1) You cannot reply directly to the user.  \n2) If you need the user to clarify or provide missing details, you must include your question(s) in the content of the output from 'switch_personas.” Because you can’t speak directly to the user as thinker, your question(s) must appear in that tool response so the 'agent” persona can relay them.\n\nWhen the user’s answer arrives (i.e., after they respond to a question from the thinker persona):  \n- Your next message must exclusively be another 'switch_personas” call to thinker. Do not perform any other tool calls or provide final answers before doing this.  \n- Only after you switch back to thinker can you interpret the new user input, reason about the next steps, or decide on final actions.  \n\nOnce you have all necessary details/clarifications from the user and you have reasoned through the solution as the thinker, switch back to 'agent” one last time to provide the final answer or perform the next relevant tool actions. At that point, you may respond directly to the user again.\n\nAdditional Guidance:  \n- Use the 'scrape_urls” function for webpage information. By default, set 'use_cache” to True for static or less dynamic content. When immediate real-time data is needed (e.g., real-time scores or financial updates), set 'use_cache” to False.  \n- When lacking a specific URL, use the 'google_search” function with a concise query to locate a page or data. Avoid using it as a stand-in for direct answers.  \n- Today’s date is {datetime.now().strftime('%B %d, %Y %H:%M:%S')}.\n\nPLEASE follow these instructions strictly, especially regarding the mandatory persona switch immediately after the user answers a question from the thinker, to keep the conversation structured and consistent.",
            }
        ],
    }
    conversation.add_message(system_message)

    tool_aggregator = ToolCallAggregator()

    # Main chat loop.
    while True:
        user_input = console.input("[bold yellow]You:[/] ")
        if user_input.lower() in ["exit", "quit"]:
            console.print("\n[bold red]Goodbye! Have a great day![/]\n")
            break

        # Add the user message.
        conversation.add_message(
            {"role": "user", "content": [{"type": "text", "text": user_input}]}
        )

        # Build the interface layout.
        layout = Layout()
        layout.split_column(
            Layout(name="spinner", size=1),
            Layout(name="content", ratio=1),
            Layout(name="tools", size=3),
        )
        spinner_text = "Thinking..."
        spinner = Spinner("dots", text=spinner_text, style="dim")
        layout["spinner"].update(spinner)
        layout["content"].update(Markdown(""))
        layout["tools"].update(build_tools_panel_from_list([]))

        try:
            # Initialize variables outside the loop
            full_response = ""
            tool_aggregator.reset()

            # Keep processing until we get a response without tool calls
            while True:
                stream = stream_message(conversation.get_history())
                with Live(
                    layout, refresh_per_second=10, console=console, transient=True
                ) as live:
                    full_response = ""  # Reset for each new response
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            content_piece = chunk.choices[0].delta.content
                            full_response += content_piece
                            layout["content"].update(Markdown(full_response))
                        if chunk.choices[0].delta.tool_calls:
                            tool_aggregator.process_delta(
                                chunk.choices[0].delta.tool_calls
                            )
                            current_calls = tool_aggregator.get_all_calls()
                            if current_calls:
                                latest_call = current_calls[-1]
                                tool_name = (
                                    latest_call.function.name
                                    if hasattr(latest_call.function, "name")
                                    else str(latest_call)
                                )
                                spinner_text = (
                                    f"Detected tool call: [cyan]{tool_name}[/]..."
                                )
                                layout["spinner"].update(
                                    Spinner("dots", text=spinner_text, style="dim")
                                )
                                layout["tools"].update(
                                    build_tools_panel_from_list(current_calls)
                                )
                        live.update(layout)

                    tool_aggregator.finalize()
                    layout["spinner"].update("")
                    layout["tools"].update(
                        build_tools_panel_from_list(tool_aggregator.get_all_calls())
                    )
                    live.update(layout)

                # Process any tool calls
                tool_calls = tool_aggregator.get_all_calls()
                if not tool_calls:  # If no tool calls, we're done
                    break

                # Add the assistant's message with tool calls
                conversation.add_message(
                    {
                        "role": "assistant",
                        "content": [],
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments,
                                },
                            }
                            for tool_call in tool_calls
                        ],
                    }
                )

                console.print("\n[bold cyan]Processing tool calls...[/]")
                for tool_call in tool_calls:
                    try:
                        # Debug: Print the raw arguments
                        console.print(
                            f"[dim]Raw arguments: {tool_call.function.arguments}[/]"
                        )

                        if (
                            not tool_call.function.arguments
                            or tool_call.function.arguments.isspace()
                        ):
                            console.print(
                                "[yellow]Skipping tool call with empty arguments[/]"
                            )
                            continue

                        args_str = tool_call.function.arguments.strip()
                        if not (args_str.startswith("{") and args_str.endswith("}")):
                            console.print(
                                "[yellow]Malformed JSON arguments, skipping[/]"
                            )
                            continue

                        arguments = json.loads(args_str)
                        tool_call_dict = {
                            "id": tool_call.id,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": arguments,
                            },
                        }
                        console.print(f"[dim]Executing {tool_call.function.name}...[/]")
                        tool_result = dispatch_tool_call(tool_call_dict)
                        console.print(f"[dim]Tool result: {tool_result}[/]")
                        conversation.add_message(
                            {
                                "role": "tool",
                                "content": [{"type": "text", "text": str(tool_result)}],
                                "tool_call_id": tool_call.id,
                            }
                        )
                    except Exception as e:
                        console.print(f"[red]Error calling tool: {str(e)}[/]")

                tool_aggregator.reset()

            # Add the final assistant message without tool calls
            console.print("\n[bold blue]Assistant:[/]")
            console.print(Markdown(full_response))
            conversation.add_message(
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": full_response}],
                }
            )

        except Exception as e:
            console.print(f"\n[bold red]Error:[/] {e}\n")


if __name__ == "__main__":
    chat_cli()
