#!/usr/bin/env python3
import os
import json
import click
import logging
from rich.console import Console
from rich.markdown import Markdown
from rich.layout import Layout
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live
from rich.logging import RichHandler
from datetime import datetime
import tiktoken

from conversation import Conversation
from llm_client import stream_message
from tool_dispatcher import dispatch_tool_call
from orchestrator import Orchestrator, Task
from utils import setup_logging

# Setup console for rich output
console = Console()

# Setup logging with RichHandler for better formatting
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
logger = logging.getLogger("research_bot")


def build_tools_panel_from_list(calls_list):
    if not calls_list:
        return Panel("No tool calls", title="Tool Calls")
    text = "\n".join(
        [f"{i+1}. {call['function']['name']}" for i, call in enumerate(calls_list)]
    )
    return Panel(text, title="Tool Calls")


def build_scratchpad_panel(scratchpad_state):
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
    citations = []
    if tool_name == "google_search":
        items = result.get("items", [])
        for item in items:
            title = item.get("title", "No title")
            display = item.get("displayLink", "Unknown source")
            link = item.get("link", "No URL")
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


scratchpad_state = {}


class ToolCallAggregator:
    def __init__(self):
        self.final_tool_calls = {}

    def reset(self):
        self.final_tool_calls = {}

    def process_delta(self, tool_calls):
        if not tool_calls:
            return
        calls = tool_calls if isinstance(tool_calls, list) else [tool_calls]
        for tool_call in calls:
            index = tool_call.index
            if index not in self.final_tool_calls:
                self.final_tool_calls[index] = {
                    "index": index,
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                    "id": tool_call.id if tool_call.id else None,
                }
            if tool_call.id and self.final_tool_calls[index]["id"] is None:
                self.final_tool_calls[index]["id"] = tool_call.id
            if tool_call.function:
                if tool_call.function.name:
                    self.final_tool_calls[index]["function"][
                        "name"
                    ] = tool_call.function.name
                if tool_call.function.arguments:
                    self.final_tool_calls[index]["function"][
                        "arguments"
                    ] += tool_call.function.arguments

    def get_all_calls(self):
        return list(self.final_tool_calls.values())

    def finalize(self):
        pass


conversation = Conversation()


@click.command()
@click.option("--debug", is_flag=True, help="Enable debug mode for detailed logging")
def chat_cli(debug):
    """CLI for the research bot."""
    # Adjust logging level based on debug flag
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

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
    orchestrator = Orchestrator()

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
                            tool_name = latest_call["function"]["name"]
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
            final_response = full_response
            layout["spinner"].update("")
            layout["tools"].update(
                build_tools_panel_from_list(tool_aggregator.get_all_calls())
            )
            layout["scratchpad"].update(build_scratchpad_panel(scratchpad_state))
            tool_calls = tool_aggregator.get_all_calls()

            if tool_calls:
                # Use logger for debug messages and Rich for user-friendly updates
                if debug:
                    console.print("[bold cyan]Processing tool calls...[/]")
                else:
                    spinner_text = "Processing tool calls..."
                    layout["spinner"].update(
                        Spinner("dots", text=spinner_text, style="dim")
                    )
                    live.update(layout)

                # Add assistant message with tool_calls
                assistant_message = {
                    "role": "assistant",
                    "content": [],
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["function"]["name"],
                                "arguments": tc["function"]["arguments"],
                            },
                        }
                        for tc in tool_calls
                    ],
                }
                conversation.add_message(assistant_message)

                for tc in tool_calls:
                    try:
                        raw_args = tc["function"]["arguments"]
                        logger.debug(f"Raw arguments: {raw_args}")
                        if not raw_args or raw_args.isspace():
                            logger.warning("Skipping empty-argument tool call")
                            continue
                        args_obj = json.loads(raw_args)
                        result = dispatch_tool_call(
                            {
                                "id": tc["id"],
                                "function": {
                                    "name": tc["function"]["name"],
                                    "arguments": args_obj,
                                },
                            },
                            conversation=conversation,
                            scratchpad_state=scratchpad_state,
                        )
                        logger.debug(f"Tool result: {result}")

                        if tc["function"]["name"] in ("scrape_urls", "google_search"):
                            citation_text = generate_mla_citation(
                                tc["function"]["name"], result
                            )
                            scratchpad_state[tc["id"]] = {
                                "title": tc["function"]["name"],
                                "content": citation_text,
                            }
                            result = f"{result}\n\nMLA Citation(s):\n{citation_text}"

                        # Add tool message
                        tool_message = {
                            "role": "tool",
                            "content": [{"type": "text", "text": str(result)}],
                            "tool_call_id": tc["id"],
                        }
                        conversation.add_message(tool_message)

                        # Add tasks to orchestrator based on tool results
                        if tc["function"]["name"] == "google_search":
                            task_id = f"retrieval_{tc['id']}"
                            task = Task(
                                task_id=task_id,
                                task_type="retrieval",
                                params={"query": args_obj["q"]},
                            )
                            orchestrator.add_task(task)
                        elif tc["function"]["name"] == "scrape_urls":
                            for url in args_obj["urls"]:
                                task_id = f"retrieval_url_{tc['id']}_{url}"
                                task = Task(
                                    task_id=task_id,
                                    task_type="retrieval",
                                    params={"url": url},
                                )
                                orchestrator.add_task(task)
                    except Exception as ex:
                        logger.error(f"Tool call error: {ex}")

                # Execute tasks using orchestrator
                orchestrator.execute_tasks()
                task_results = orchestrator.get_task_results()

                # Add synthesis task based on retrieval results
                for task_id, result in task_results.items():
                    if task_id.startswith("retrieval_"):
                        synthesis_task = Task(
                            task_id=f"synthesis_{task_id}",
                            task_type="synthesis",
                            params={"query": user_input, "data": str(result)},
                            dependencies=[task_id],
                        )
                        orchestrator.add_task(synthesis_task)

                # Execute synthesis tasks
                orchestrator.execute_tasks()
                synthesis_results = orchestrator.get_task_results()

                # Add validation task for synthesis results
                for task_id, result in synthesis_results.items():
                    if task_id.startswith("synthesis_"):
                        validation_task = Task(
                            task_id=f"validation_{task_id}",
                            task_type="validation",
                            params={"summary": result, "sources": str(task_results)},
                            dependencies=[task_id],
                        )
                        orchestrator.add_task(validation_task)

                # Execute validation tasks
                orchestrator.execute_tasks()
                final_results = orchestrator.get_task_results()

                # Use final validated results for response
                final_response = "\n".join(
                    [
                        result
                        for task_id, result in final_results.items()
                        if task_id.startswith("validation_")
                    ]
                )
                if not final_response:
                    final_response = full_response

                if debug:
                    console.print(
                        "[magenta]\nNow calling LLM WITHOUT scratchpad tools...[/]"
                    )
                else:
                    spinner_text = "Generating final response..."
                    layout["spinner"].update(
                        Spinner("dots", text=spinner_text, style="dim")
                    )
                    live.update(layout)

                filtered_history = conversation.get_history_excluding_scratchpad_msgs()

                # Log the conversation history for debugging
                logger.debug(
                    f"Conversation history for second LLM call: {filtered_history}"
                )

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
                    second_response if second_response.strip() else final_response
                )
            else:
                final_text = final_response

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
            logger.error(f"Error: {e}")
            console.print(f"\n[bold red]Error:[/] {e}\n")


if __name__ == "__main__":
    chat_cli()
