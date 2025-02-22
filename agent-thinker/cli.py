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


def build_scratchpad_panel(scratchpad_state):
    """
    Builds a Rich Panel showing the current contents of the scratchpad.
    """
    if not scratchpad_state:
        return Panel("No scratchpad entries", title="Scratchpad")

    lines = []
    for eid, note in scratchpad_state.items():
        title = note["title"]
        content = note["content"]
        lines.append(f"[bold]ID {eid}[/bold]: {title}\n{content}\n")
    panel_text = "\n".join(lines)
    return Panel(panel_text, title="Scratchpad")


def generate_mla_citation(tool_name, result):
    """
    Given the tool name and its result dictionary, generate an MLA-style citation.
    """
    citations = []
    if tool_name == "google_search":
        items = result.get("items", [])
        for item in items:
            title = item.get("title", "No title")
            display = item.get("displayLink", "Unknown source")
            link = item.get("link", "No URL")
            # Simple MLA citation format: "Title." DisplayLink, URL.
            citation = f'"{title}." {display}, {link}.'
            citations.append(citation)
    elif tool_name == "scrape_urls":
        data = result.get("data", [])
        for entry in data:
            meta = entry.get("metadata", {})
            url = meta.get("url", "No URL")
            title = meta.get("title", "No title")
            citation = f'"{title}." {url}.'
            citations.append(citation)
    return "\n".join(citations)


# Global scratchpad state (accumulates citations from tool calls)
scratchpad_state = {}


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
            chunked_content += f"\n<start chunk {i}>\n{chunk}\n<end chunk {i}>\n"
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
                    "- Interact with tools (including scratchpad tools),\n"
                    "- Reply directly to the user.\n\n"
                    "When facing a complex/multi-step request, you must switch to your 'thinker' persona by calling "
                    "the 'switch_personas' function with argument \"thinker\". Then once enough details are gathered, switch back to 'agent' and provide a final answer.\n\n"
                    f"Today's date is {datetime.now().strftime('%B %d, %Y %H:%M:%S')}."
                ),
            }
        ],
    }
    conversation.add_message(system_message)
    tool_aggregator = ToolCallAggregator()

    while True:
        user_input = console.input("[bold yellow]You:[/] ")
        if user_input.lower() in ("exit", "quit"):
            console.print("[bold red]Goodbye![/]")
            break

        conversation.add_message(
            {
                "role": "user",
                "content": [{"type": "text", "text": user_input}],
            }
        )

        # Build initial layout
        layout = Layout()
        layout.split_column(
            Layout(name="spinner", size=1), Layout(name="main", ratio=1)
        )
        layout["main"].split_row(
            Layout(name="content", ratio=1),
            Layout(name="tools", size=35),
            Layout(name="scratchpad", size=35),
        )

        spinner_text = "Thinking..."
        spinner = Spinner("dots", text=spinner_text, style="dim")
        layout["spinner"].update(spinner)
        layout["content"].update(Markdown(""))
        layout["tools"].update(build_tools_panel_from_list([]))
        layout["scratchpad"].update(build_scratchpad_panel(scratchpad_state))

        try:
            full_response = ""
            tool_aggregator.reset()

            # (A) First LLM call WITH scratchpad tools
            stream = stream_message(
                conversation.get_history(),
                # (Assuming stream_message ignores use_scratchpad if not implemented)
            )

            with Live(
                layout, refresh_per_second=10, console=console, transient=True
            ) as live:
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content_piece = chunk.choices[0].delta.content
                        full_response += content_piece
                        layout["content"].update(Markdown(full_response))
                    if chunk.choices[0].delta.tool_calls:
                        tool_aggregator.process_delta(chunk.choices[0].delta.tool_calls)
                        current_calls = tool_aggregator.get_all_calls()
                        if current_calls:
                            latest_call = current_calls[-1]
                            tool_name = latest_call.function.name
                            spinner_text = f"Tool call: [cyan]{tool_name}[/]"
                            layout["spinner"].update(
                                Spinner("dots", text=spinner_text, style="dim")
                            )
                            layout["tools"].update(
                                build_tools_panel_from_list(current_calls)
                            )
                    layout["scratchpad"].update(
                        build_scratchpad_panel(scratchpad_state)
                    )
                    live.update(layout)

            tool_aggregator.finalize()
            layout["spinner"].update("")
            layout["tools"].update(
                build_tools_panel_from_list(tool_aggregator.get_all_calls())
            )
            layout["scratchpad"].update(build_scratchpad_panel(scratchpad_state))
            tool_calls = tool_aggregator.get_all_calls()

            if tool_calls:
                # Add the assistant message that triggered these tool calls.
                conversation.add_message(
                    {
                        "role": "assistant",
                        "content": [],
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in tool_calls
                        ],
                    }
                )
                console.print("[bold cyan]Processing tool calls...[/]")
                for tc in tool_calls:
                    try:
                        raw_args = tc.function.arguments
                        console.print(f"[dim]Raw arguments: {raw_args}[/]")
                        if not raw_args or raw_args.isspace():
                            console.print(
                                "[yellow]Skipping empty-argument tool call[/]"
                            )
                            continue
                        args_obj = json.loads(raw_args)
                        result = dispatch_tool_call(
                            {
                                "id": tc.id,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": args_obj,
                                },
                            },
                            conversation=conversation,
                        )
                        console.print(f"[dim]Tool result: {result}[/]")

                        # If the tool call is a search or scrape, generate an MLA citation and update the scratchpad.
                        if tc.function.name in ("scrape_urls", "google_search"):
                            citation_text = generate_mla_citation(
                                tc.function.name, result
                            )
                            scratchpad_state[tc.id] = {
                                "title": tc.function.name,
                                "content": citation_text,
                            }
                            result = f"{result}\n\nMLA Citation(s):\n{citation_text}"

                        conversation.add_message(
                            {
                                "role": "tool",
                                "content": [{"type": "text", "text": str(result)}],
                                "tool_call_id": tc.id,
                            }
                        )
                    except Exception as ex:
                        console.print(f"[red]Tool call error: {ex}[/]")

                # (B) Second LLM call WITHOUT scratchpad tools.
                console.print(
                    "[magenta]\nNow calling LLM WITHOUT scratchpad tools...[/]"
                )
                filtered_history = conversation.get_history_excluding_scratchpad_msgs()

                second_aggregator = ToolCallAggregator()
                second_response = ""
                layout["spinner"].update(
                    Spinner("dots", text="Second pass...", style="dim")
                )
                with Live(
                    layout, refresh_per_second=10, console=console, transient=True
                ) as live2:
                    second_stream = stream_message(
                        messages=filtered_history,
                    )
                    for chunk in second_stream:
                        if chunk.choices[0].delta.content:
                            piece = chunk.choices[0].delta.content
                            second_response += piece
                            layout["content"].update(Markdown(second_response))
                        if chunk.choices[0].delta.tool_calls:
                            second_aggregator.process_delta(
                                chunk.choices[0].delta.tool_calls
                            )
                        layout["tools"].update(
                            build_tools_panel_from_list(
                                second_aggregator.get_all_calls()
                            )
                        )
                        layout["scratchpad"].update(
                            build_scratchpad_panel(scratchpad_state)
                        )
                        live2.update(layout)

                second_aggregator.finalize()
                layout["spinner"].update("")
                layout["tools"].update(
                    build_tools_panel_from_list(second_aggregator.get_all_calls())
                )
                layout["scratchpad"].update(build_scratchpad_panel(scratchpad_state))
                final_text = (
                    second_response if second_response.strip() else full_response
                )
            else:
                final_text = full_response

            # Final non-transient rendering
            console.print("\n[bold blue]Final Rendering with Scratchpad:[/]")
            final_layout = Layout()
            final_layout.split_column(
                Layout(name="final_spinner", size=1),
                Layout(name="final_main", ratio=1),
            )
            final_layout["final_main"].split_row(
                Layout(name="final_content", ratio=1),
                Layout(name="final_tools", size=35),
                Layout(name="final_scratchpad", size=35),
            )
            final_layout["final_content"].update(Markdown(final_text))
            final_layout["final_tools"].update(build_tools_panel_from_list(tool_calls))
            final_layout["final_scratchpad"].update(
                build_scratchpad_panel(scratchpad_state)
            )
            with Live(
                final_layout, refresh_per_second=2, console=console, transient=False
            ):
                pass

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
