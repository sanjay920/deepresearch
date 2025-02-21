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
import tiktoken

from conversation import Conversation
from llm_client import stream_message
from tool_dispatcher import dispatch_tool_call


def build_tools_panel_from_list(calls_list):
    if not calls_list:
        return Panel("No tool calls", title="Tool Calls")
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
        calls = tool_calls if isinstance(tool_calls, list) else [tool_calls]
        for tool_call in calls:
            index = tool_call.index
            if index not in self.final_tool_calls:
                self.final_tool_calls[index] = tool_call
                if not hasattr(self.final_tool_calls[index].function, "arguments"):
                    self.final_tool_calls[index].function.arguments = ""
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

    def chunk_tool_output(self, content: str, chunk_size: int = 2000) -> str:
        """Chunks tool output content to stay within token limits.

        Args:
            content: The tool output content to chunk
            chunk_size: Maximum number of tokens per chunk (default 2000)

        Returns:
            Chunked content with markers
        """
        enc = tiktoken.get_encoding("cl100k_base")

        sections = []
        current_section = []

        for line in content.splitlines():
            if (
                line.startswith("#")
                or line.startswith("[")
                or line.startswith("!")
                or len("".join(current_section)) > 500
            ):
                if current_section:
                    sections.append("\n".join(current_section))
                    current_section = []
            current_section.append(line)

        if current_section:
            sections.append("\n".join(current_section))

        chunks = []
        current_chunk = []
        current_chunk_tokens = 0

        for section in sections:
            section_tokens = enc.encode(section)
            section_token_count = len(section_tokens)

            if section_token_count > chunk_size:
                words = section.split()
                temp_chunk = []
                temp_tokens = 0

                for word in words:
                    word_tokens = len(enc.encode(word + " "))
                    if temp_tokens + word_tokens > chunk_size:
                        if temp_chunk:
                            chunks.append(" ".join(temp_chunk))
                        temp_chunk = [word]
                        temp_tokens = word_tokens
                    else:
                        temp_chunk.append(word)
                        temp_tokens += word_tokens

                if temp_chunk:
                    chunks.append(" ".join(temp_chunk))

            elif current_chunk_tokens + section_token_count > chunk_size:
                chunks.append("\n".join(current_chunk))
                current_chunk = [section]
                current_chunk_tokens = section_token_count
            else:
                current_chunk.append(section)
                current_chunk_tokens += section_token_count

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        chunked_content = ""
        for i, chunk in enumerate(chunks, 1):
            chunked_content += f"\n<start chunk {i}>\n"
            chunked_content += chunk
            chunked_content += f"\n<end chunk {i}>\n"

        return chunked_content


console = Console()
conversation = Conversation()


@click.command()
def chat_cli():
    system_message = {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": (
                    "You are an assistant wearing your 'agent' hat. This means you can:\n"
                    "- Interact with tools,\n- Reply directly to the user.\n\n"
                    "When facing a complex/multi-step request, you must switch to your 'thinker' persona by calling "
                    "the 'switch_personas' function with argument \"thinker\". As thinker, you generate a plan or ask clarifying "
                    "questions—but you are not allowed to respond directly to the user.\n\n"
                    "Once enough details are gathered and you have reasoned through a solution, switch back to 'agent' and "
                    "provide the final answer. In addition, if you wish to respond directly in a final answer, set the JSON key "
                    '"respond_to_user" to true in your output. If your output merely provides your plan, include an "action": "plan" '
                    "field in your output. The main CLI loop, which has access to search and webpage extraction tools, will then use "
                    "your plan to trigger the appropriate research before generating a final answer.\n\n"
                    f"Today's date is {datetime.now().strftime('%B %d, %Y %H:%M:%S')}."
                ),
            }
        ],
    }
    conversation.add_message(system_message)

    tool_aggregator = ToolCallAggregator()

    while True:
        user_input = console.input("[bold yellow]You:[/] ")
        if user_input.lower() in ["exit", "quit"]:
            console.print("\n[bold red]Goodbye! Have a great day![/]\n")
            break

        conversation.add_message(
            {"role": "user", "content": [{"type": "text", "text": user_input}]}
        )

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
            full_response = ""
            tool_aggregator.reset()

            bypass_llm = False
            final_response = None

            while True:
                stream = stream_message(conversation.get_history())
                with Live(
                    layout, refresh_per_second=10, console=console, transient=True
                ) as live:
                    full_response = ""
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

                tool_calls = tool_aggregator.get_all_calls()
                if not tool_calls:
                    break

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

                        if tool_call.function.name == "switch_personas":
                            console.print(
                                f"[dim]Switching to {arguments['switch_to']} persona...[/]"
                            )
                            spinner_text = "[cyan]Waiting for thinker to process...[/]"
                            layout["spinner"].update(
                                Spinner("dots", text=spinner_text, style="bold")
                            )
                            thinking_level = arguments.get("thinking_level", "high")

                            try:
                                tool_result = dispatch_tool_call(
                                    tool_call_dict,
                                    conversation=conversation,
                                    thinking_level=thinking_level,
                                )
                                if tool_result is None:
                                    raise ValueError(
                                        "Received empty response from thinker"
                                    )
                                result = json.loads(tool_result)
                                action = result.get("action", "final")
                                if action == "plan":
                                    formatted_result = (
                                        f"Here's my plan:\n{result['text']}"
                                    )
                                    console.print(
                                        f"[dim]Thinker plan output: {formatted_result}[/]"
                                    )
                                    conversation.add_message(
                                        {
                                            "role": "tool",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": formatted_result,
                                                }
                                            ],
                                            "tool_call_id": tool_call.id,
                                        }
                                    )
                                    conversation.add_message(
                                        {
                                            "role": "assistant",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": formatted_result,
                                                }
                                            ],
                                            "plan": True,
                                        }
                                    )

                                elif action == "questions":
                                    formatted_result = f"Here are some questions I need answered:\n{result['text']}"
                                    console.print(
                                        f"[dim]Thinker questions output: {formatted_result}[/]"
                                    )
                                    conversation.add_message(
                                        {
                                            "role": "tool",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": formatted_result,
                                                }
                                            ],
                                            "tool_call_id": tool_call.id,
                                        }
                                    )
                                    break

                                elif (
                                    result.get("respond_to_user", False)
                                    or action == "final"
                                ):
                                    formatted_result = f"{result.get('text')}"
                                    console.print(
                                        f"[dim]Thinker final answer: {formatted_result}[/]"
                                    )
                                    conversation.add_message(
                                        {
                                            "role": "tool",
                                            "content": [
                                                {
                                                    "type": "text",
                                                    "text": formatted_result,
                                                }
                                            ],
                                            "tool_call_id": tool_call.id,
                                        }
                                    )
                                    final_response = formatted_result
                                    bypass_llm = True
                                    break
                            except Exception as e:
                                error_response = json.dumps(
                                    {
                                        "action": "questions",
                                        "text": "I apologize, but I encountered an error while processing. Let me try a different approach.",
                                        "respond_to_user": False,
                                    }
                                )
                                conversation.add_message(
                                    {
                                        "role": "tool",
                                        "content": [
                                            {"type": "text", "text": error_response}
                                        ],
                                        "tool_call_id": tool_call.id,
                                    }
                                )
                                raise e
                        else:
                            console.print(
                                f"[dim]Executing {tool_call.function.name}...[/]"
                            )
                            tool_result = dispatch_tool_call(tool_call_dict)
                            console.print(f"[dim]Tool result: {tool_result}[/]")
                            conversation.add_message(
                                {
                                    "role": "tool",
                                    "content": [
                                        {"type": "text", "text": str(tool_result)}
                                    ],
                                    "tool_call_id": tool_call.id,
                                }
                            )
                    except Exception as e:
                        console.print(f"[red]Error calling tool: {str(e)}[/]")

                tool_aggregator.reset()
                if bypass_llm:
                    break

            console.print("\n[bold blue]Assistant:[/]")
            final_text = final_response if bypass_llm else full_response
            console.print(Markdown(final_text))
            if not bypass_llm:
                conversation.add_message(
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": final_text}],
                    }
                )

        except Exception as e:
            console.print(f"\n[bold red]Error:[/] {e}\n")


if __name__ == "__main__":
    chat_cli()
