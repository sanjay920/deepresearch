#!/usr/bin/env python3
import os
import click
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.layout import Layout
from rich.panel import Panel
from rich.spinner import Spinner
from rich.live import Live

try:
    from rich.console import Console
    from rich.markdown import Markdown
except ImportError:
    raise ImportError(
        "This script requires the 'rich' library for Markdown rendering.\n"
        "Please install it with:\n\n  pip install rich"
    )

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
SYSTEM_PROMPT_TEXT = 'You are an assistant wearing your “agent” hat. This means you can:  \n• Interact with tools,  \n• Reply directly to the user.\n\nIf you face a complex or multi-step request (e.g., data analysis, multi-step reasoning, or tasks that require gathering and synthesizing external information), you must switch to your “thinker” persona. Do this by calling the “switch_personas” function with the argument "thinker".\n\nWhile wearing the “thinker” hat:  \n1) You cannot reply directly to the user.  \n2) If you need the user to clarify or provide missing details, you must include your question(s) in the content of the output from “switch_personas.” Because you can’t speak directly to the user as thinker, your question(s) must appear in that tool response so the “agent” persona can relay them.\n\nWhen the user’s answer arrives (i.e., after they respond to a question from the thinker persona):  \n• Your next message must exclusively be another “switch_personas” call to thinker. Do not perform any other tool calls or provide final answers before doing this.  \n• Only after you switch back to thinker can you interpret the new user input, reason about the next steps, or decide on final actions.  \n\nOnce you have all necessary details/clarifications from the user and you have reasoned through the solution as the thinker, switch back to “agent” one last time to provide the final answer or perform the next relevant tool actions. At that point, you may respond directly to the user again.\n\nAdditional Guidance:  \n• Use the “scrape_urls” function for webpage information. By default, set “use_cache” to True for static or less dynamic content. When immediate real-time data is needed (e.g., real-time scores or financial updates), set “use_cache” to False.  \n• When lacking a specific URL, use the “google_search” function with a concise query to locate a page or data. Avoid using it as a stand-in for direct answers.  \n• Today’s date is Feb 14, 2025.\n\nPLEASE follow these instructions strictly, especially regarding the mandatory persona switch immediately after the user answers a question from the thinker, to keep the conversation structured and consistent.'
SYSTEM_PROMPT = {
    "role": "system",
    "content": [
        {
            "type": "text",
            "text": SYSTEM_PROMPT_TEXT,
        }
    ],
}

tools = [
    {
        "type": "function",
        "function": {
            "name": "scrape_urls",
            "strict": True,
            "parameters": {
                "type": "object",
                "required": ["urls", "use_cache"],
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "A single URL of a webpage",
                        },
                        "description": "An array of string URLs of the webpages to scrape",
                    },
                    "use_cache": {
                        "type": "boolean",
                        "description": "Flag to indicate whether to use cached data (default is true). Set to false when fetching a webpage with live info such as espn.com/nba/scoreboard or anything with dynamic content",
                    },
                },
                "additionalProperties": False,
            },
            "description": "Scrapes a webpage and returns its markdown equivalent",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "switch_personas",
            "strict": True,
            "parameters": {
                "type": "object",
                "required": ["switch_to", "justification", "thinking_level"],
                "properties": {
                    "switch_to": {
                        "enum": ["thinker"],
                        "type": "string",
                        "description": "The persona to switch to. Thinker helps the assistant plan out and synthesize information",
                    },
                    "justification": {
                        "type": "string",
                        "description": "Reason for why the assistant has decided to take a pause and think",
                    },
                    "thinking_level": {
                        "enum": ["high", "medium", "low"],
                        "type": "string",
                        "description": "Amount of thinking the subconscience will do. High will make the user wait longer but think better.",
                    },
                },
                "additionalProperties": False,
            },
            "description": "Ability to switch personas in the middle of the conversation",
        },
    },
    {
        "type": "function",
        "function": {
            "name": "google_search",
            "strict": True,
            "parameters": {
                "type": "object",
                "required": ["q"],
                "properties": {
                    "q": {"type": "string", "description": "The search query string."}
                },
                "additionalProperties": False,
            },
            "description": "Performs a Google search with the specified query and returns results.",
        },
    },
]


# Helper to build the tools panel from a list of tool calls
def build_tools_panel_from_list(tool_calls_list):
    if not tool_calls_list:
        return Panel("No tools called yet", title="Tool Calls")
    lines = []
    for call in tool_calls_list:
        f = call["function"]
        lines.append(
            f"- [bold]{call['type']}[/] -> [cyan]{f['name']}[/]\n  Args: {f['arguments']}"
        )
    return Panel("\n".join(lines), title="Tool Calls")


class ToolCallAggregator:
    def __init__(self):
        self.reset()

    def reset(self):
        """Reset the aggregator for a new message"""
        self.current_call = None
        self.completed_calls = []

    def process_delta(self, tool_calls):
        if not tool_calls:
            return
        for tc in tool_calls:
            # Start new tool call if we get an ID
            if tc.id and (not self.current_call or tc.id != self.current_call["id"]):
                if self.current_call:
                    self.completed_calls.append(self.current_call)
                self.current_call = {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments or "",
                    },
                }
            # Append to existing call
            elif self.current_call and tc.function.arguments:
                self.current_call["function"]["arguments"] += tc.function.arguments

    def get_all_calls(self):
        """Returns all calls including the current one if it exists"""
        result = self.completed_calls.copy()
        if self.current_call:
            result.append(self.current_call)
        return result

    def finalize(self):
        """Finalizes current call if any"""
        if self.current_call:
            self.completed_calls.append(self.current_call)
            self.current_call = None


@click.command()
def chat_cli():
    console = Console()
    conversation = [SYSTEM_PROMPT]

    console.print("[bold green]Welcome to Sanjay's Agent CLI[/]")
    console.print("Type your message and press Enter. Type [red]exit[/] to quit.\n")

    tool_aggregator = ToolCallAggregator()

    while True:
        user_input = console.input("[bold yellow]You:[/] ")
        if user_input.lower() in ["exit", "quit"]:
            console.print("\n[bold red]Goodbye! Have a great day![/]\n")
            break

        # Reset the tool aggregator for each new message
        tool_aggregator.reset()

        conversation.append(
            {"role": "user", "content": [{"type": "text", "text": user_input}]}
        )

        try:
            stream = client.chat.completions.create(
                model="gpt-4o",
                messages=conversation,
                temperature=0.06,
                top_p=1,
                max_tokens=1000,
                frequency_penalty=0,
                presence_penalty=0,
                stream=True,
                tools=tools,
            )

            full_response = ""

            # Create a layout with three panels: spinner, content, and tool calls
            layout = Layout()
            layout.split_column(
                Layout(name="spinner", size=1),
                Layout(name="content", size=10),  # Set reasonable default size
                Layout(name="tools", size=3),  # Reduce tool panel size
            )

            spinner_text = "Thinking..."
            spinner = Spinner("dots", text=spinner_text, style="dim")
            layout["spinner"].update(spinner)
            layout["content"].update(Markdown(full_response or ""))
            layout["tools"].update(build_tools_panel_from_list([]))

            with Live(
                layout,
                refresh_per_second=10,
                console=console,
                transient=True,  # Change to True to avoid duplicate output
                auto_refresh=True,
            ) as live:
                for chunk in stream:
                    delta = chunk.choices[0].delta

                    if delta.content is not None:
                        full_response += delta.content
                        layout["content"].update(Markdown(full_response))

                    if delta.tool_calls is not None:
                        tool_aggregator.process_delta(delta.tool_calls)
                        current_calls = tool_aggregator.get_all_calls()
                        if current_calls:
                            spinner_text = f"Using tool: [cyan]{current_calls[-1]['function']['name']}[/]..."
                            layout["tools"].update(
                                build_tools_panel_from_list(current_calls)
                            )
                        spinner = Spinner("dots", text=spinner_text, style="dim")
                        layout["spinner"].update(spinner)

                    live.update(layout)

                tool_aggregator.finalize()
                # Clear the spinner once streaming is done.
                layout["spinner"].update("")
                layout["tools"].update(
                    build_tools_panel_from_list(tool_aggregator.get_all_calls())
                )
                live.update(layout)

            # After streaming, show final response in a cleaner format
            console.print()  # Single line break
            console.print("[bold blue]Assistant:[/]")
            console.print(Markdown(full_response))
            if (
                tool_aggregator.get_all_calls()
            ):  # Only show tool panel if there were calls
                console.print(
                    build_tools_panel_from_list(tool_aggregator.get_all_calls())
                )
            console.print()  # Single line break

            conversation.append(
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": full_response}],
                }
            )

        except Exception as e:
            console.print(f"\n[bold red]Error:[/] {str(e)}\n")


if __name__ == "__main__":
    chat_cli()
