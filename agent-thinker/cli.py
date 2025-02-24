#!/usr/bin/env python3
import os
import json
import click
import logging
from rich.console import Console
from rich.markdown import Markdown
from threading import Thread
from datetime import datetime
import tiktoken

from conversation import Conversation
from llm_client import stream_message
from tool_dispatcher import dispatch_tool_call
from orchestrator import Orchestrator, Task
from utils import setup_logging

console = Console()


class ToolCallAggregator:
    def __init__(self):
        self.final_tool_calls = {}

    def reset(self):
        """Reset the aggregator for a new response."""
        self.final_tool_calls = {}

    def process_delta(self, tool_calls):
        """Process a delta chunk of tool calls."""
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
        """Return all aggregated tool calls."""
        return list(self.final_tool_calls.values())

    def finalize(self):
        """Finalize the aggregation process (currently a no-op)."""
        pass


@click.command()
@click.option("--debug", is_flag=True, help="Enable debug mode for detailed logging")
@click.option("--show-validation", is_flag=True, help="Show detailed validation report")
def chat_cli(debug: bool, show_validation: bool):
    """CLI interface for interacting with the assistant and generating reports."""
    setup_logging(verbose=debug)

    system_message = {
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": (
                    "You are an assistant wearing your 'agent' hat. Your goal is to fully answer the user's query by gathering and processing data. You can:\n"
                    "- Use 'google_search' to find relevant sources.\n"
                    "- Use 'scrape_urls' to fetch full content from specific websites when search snippets aren’t enough.\n"
                    "- Iterate by adding more searches or scrapes if initial data is incomplete.\n"
                    "- Use scratchpad tools to store intermediate data if needed.\n\n"
                    "For queries requiring specific details (e.g., lists, ages), follow this flow:\n"
                    "1. Start with a broad search to identify sources.\n"
                    "2. Scrape relevant websites to get detailed data.\n"
                    "3. If data is missing, queue more searches or scrapes to fill gaps.\n"
                    "4. Synthesize and validate the final answer with all collected data.\n\n"
                    "Don’t suggest users visit links—fetch the data yourself and provide a complete answer. "
                    "For complex tasks, call 'switch_personas' with 'thinker' to plan multi-step processes. "
                    f"Today’s date is {datetime.now().strftime('%B %d, %Y')}. Calculate ages based on birth dates relative to this date."
                ),
            }
        ],
    }

    conversation = Conversation()
    conversation.add_message(system_message)
    tool_aggregator = ToolCallAggregator()
    orchestrator = Orchestrator()
    scratchpad_state = {}  # Initialize persistent scratchpad state

    while True:
        user_input = console.input("[bold yellow]You:[/] ")
        if user_input.lower() in ("exit", "quit"):
            console.print("[bold red]Goodbye![/]")
            break

        conversation.add_message(
            {"role": "user", "content": [{"type": "text", "text": user_input}]}
        )

        console.print("[dim]Currently processing: Handling your request...[/]")

        try:
            while True:
                full_response = ""
                tool_aggregator.reset()

                stream = stream_message(conversation.get_history())
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                    if chunk.choices[0].delta.tool_calls:
                        tool_aggregator.process_delta(chunk.choices[0].delta.tool_calls)
                tool_calls = tool_aggregator.get_all_calls()

                if not tool_calls:
                    console.print("\n[bold blue]Final Answer:[/]")
                    console.print(Markdown(full_response))
                    break

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
                        if not raw_args or raw_args.isspace():
                            continue
                        args_obj = json.loads(raw_args)
                        console.print(
                            f"[dim]Currently processing: {tc['function']['name']} call[/]"
                        )
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
                        if result is None:
                            result = "Tool call returned no result."
                        tool_message = {
                            "role": "tool",
                            "content": [{"type": "text", "text": str(result)}],
                            "tool_call_id": tc["id"],
                        }
                        conversation.add_message(tool_message)

                        if tc["function"]["name"] == "switch_personas":
                            thinker_response = json.loads(result)
                            if "error" in thinker_response:
                                console.print(
                                    f"[bold red]Thinker Error:[/] {thinker_response['error']}"
                                )
                                break
                            if thinker_response["action"] == "plan":
                                console.print(
                                    "[dim]Currently processing: Executing thinker’s plan[/]"
                                )
                                for step in thinker_response.get("steps", []):
                                    if step["tool"] == "google_search":
                                        task_id = f"retrieval_{tc['id']}_{step['parameters']['q']}"
                                        task = Task(
                                            task_id=task_id,
                                            task_type="retrieval",
                                            params={"query": step["parameters"]["q"]},
                                        )
                                        orchestrator.add_task(task)
                                    elif step["tool"] == "scrape_urls":
                                        for url in step["parameters"]["urls"]:
                                            task_id = f"retrieval_url_{tc['id']}_{url}"
                                            task = Task(
                                                task_id=task_id,
                                                task_type="retrieval",
                                                params={"url": url},
                                            )
                                            orchestrator.add_task(task)
                            elif thinker_response["action"] == "questions":
                                console.print("\n[bold yellow]Questions for you:[/]")
                                console.print(Markdown(thinker_response["text"]))
                                user_response = console.input(
                                    "[bold yellow]Your response:[/] "
                                )
                                conversation.add_message(
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "text", "text": user_response}
                                        ],
                                    }
                                )
                        elif tc["function"]["name"] == "google_search":
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
                        logging.error(f"Tool call error: {ex}")
                        console.print(f"[bold red]Error in tool call:[/] {str(ex)}")
                        conversation.add_message(
                            {
                                "role": "tool",
                                "content": [
                                    {"type": "text", "text": f"Error: {str(ex)}"}
                                ],
                                "tool_call_id": tc["id"],
                            }
                        )

                if orchestrator.get_pending_tasks():
                    retrieval_task_ids = [
                        task.task_id
                        for task in orchestrator.tasks.values()
                        if task.task_type == "retrieval"
                    ]
                    for retrieval_task_id in retrieval_task_ids:
                        synthesis_task = Task(
                            task_id=f"synthesis_{retrieval_task_id}",
                            task_type="synthesis",
                            params={"query": user_input},
                            dependencies=[retrieval_task_id],
                        )
                        orchestrator.add_task(synthesis_task)
                        validation_task = Task(
                            task_id=f"validation_{synthesis_task.task_id}",
                            task_type="validation",
                            params={"synthesis_task_id": synthesis_task.task_id},
                            dependencies=[synthesis_task.task_id],
                        )
                        orchestrator.add_task(validation_task)

                    console.print(
                        "[dim]Currently processing: Executing queued tasks[/]"
                    )

                    def task_start_callback(task):
                        console.print(
                            f"[dim]Currently processing: {task.get_description()}[/]"
                        )

                    thread = Thread(
                        target=orchestrator.execute_tasks,
                        kwargs={"on_task_start": task_start_callback},
                    )
                    thread.start()
                    thread.join()

                    console.print("[dim]Task execution summary:[/]")
                    for task_id, task in orchestrator.tasks.items():
                        status = task.status
                        description = task.get_description()
                        console.print(f"{task_id}: {status} - {description}")

                    synthesis_tasks = [
                        task
                        for task in orchestrator.tasks.values()
                        if task.task_type == "synthesis" and task.status == "completed"
                    ]
                    if synthesis_tasks:
                        final_synthesis = synthesis_tasks[-1].result
                        try:
                            synthesis_output = json.loads(final_synthesis)
                            if synthesis_output["status"] == "complete":
                                console.print("\n[bold blue]Final Answer:[/]")
                                console.print(Markdown(synthesis_output["summary"]))
                            else:
                                console.print(
                                    "\n[bold yellow]Partial Answer (Max Iterations Reached):[/]"
                                )
                                console.print(Markdown(synthesis_output["summary"]))
                        except json.JSONDecodeError:
                            console.print(
                                "[bold red]Error:[/] Invalid synthesis output format."
                            )
                    else:
                        console.print(
                            "[bold red]Error:[/] No synthesis results available due to task failures."
                        )
                        failed_tasks = [
                            task
                            for task in orchestrator.tasks.values()
                            if task.status == "failed"
                        ]
                        for task in failed_tasks:
                            console.print(
                                f"- Failed: {task.get_description()} - {task.result}"
                            )
                    break

        except Exception as e:
            console.print(f"\n[bold red]Error:[/] {str(e)}")
            logging.error(f"CLI error: {e}")


if __name__ == "__main__":
    chat_cli()
