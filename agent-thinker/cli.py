#!/usr/bin/env python3
import os
from openai import OpenAI
import click

try:
    from rich.console import Console
    from rich.markdown import Markdown
except ImportError:
    raise ImportError(
        "This script requires the 'rich' library for Markdown rendering.\n"
        "Please install it with:\n\n  pip install rich"
    )

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = {
    "role": "system",
    "content": [
        {
            "type": "text",
            "text": 'You are an assistant wearing your “agent” hat. This means you can:  \n• Interact with tools,  \n• Reply directly to the user.\n\nIf you face a complex or multi-step request (e.g., data analysis, multi-step reasoning, or tasks that require gathering and synthesizing external information), you must switch to your “thinker” persona. Do this by calling the “switch_personas” function with the argument "thinker".\n\nWhile wearing the “thinker” hat:  \n1) You cannot reply directly to the user.  \n2) If you need the user to clarify or provide missing details, you must include your question(s) in the content of the output from “switch_personas.” Because you can’t speak directly to the user as thinker, your question(s) must appear in that tool response so the “agent” persona can relay them.\n\nWhen the user’s answer arrives (i.e., after they respond to a question from the thinker persona):  \n• Your next message must exclusively be another “switch_personas” call to thinker. Do not perform any other tool calls or provide final answers before doing this.  \n• Only after you switch back to thinker can you interpret the new user input, reason about the next steps, or decide on final actions.  \n\nOnce you have all necessary details/clarifications from the user and you have reasoned through the solution as the thinker, switch back to “agent” one last time to provide the final answer or perform the next relevant tool actions. At that point, you may respond directly to the user again.\n\nAdditional Guidance:  \n• Use the “scrape_urls” function for webpage information. By default, set “use_cache” to True for static or less dynamic content. When immediate real-time data is needed (e.g., real-time scores or financial updates), set “use_cache” to False.  \n• When lacking a specific URL, use the “google_search” function with a concise query to locate a page or data. Avoid using it as a stand-in for direct answers.  \n• Today’s date is Feb 14, 2025.\n\nPLEASE follow these instructions strictly, especially regarding the mandatory persona switch immediately after the user answers a question from the thinker, to keep the conversation structured and consistent.',
        }
    ],
}


@click.command()
def chat_cli():
    console = Console()
    conversation = [SYSTEM_PROMPT]
    console.print("\n")
    console.rule("[bold green]Welcome to Sanjay's Agent CLI[/]", style="green")
    console.print("\nType your message and press Enter. Type [red]exit[/] to quit.\n")

    while True:
        console.rule(style="dim")
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            console.print("\n[bold red]Goodbye! Have a great day![/]\n")
            break

        with console.status("[dim]Thinking...[/]", spinner="dots"):
            conversation.append(
                {"role": "user", "content": [{"type": "text", "text": user_input}]}
            )

            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=conversation,
                    temperature=0.06,
                    top_p=1,
                    max_tokens=1000,
                    frequency_penalty=0,
                    presence_penalty=0,
                )

                assistant_message = response.choices[0].message

                conversation.append(
                    {
                        "role": "assistant",
                        "content": [
                            {"type": "text", "text": assistant_message.content}
                        ],
                    }
                )
                text_parts = []
                if isinstance(assistant_message.content, list):
                    for part in assistant_message.content:
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    rendered_text = "\n".join(text_parts)
                else:
                    rendered_text = assistant_message.content

                console.print("\nAssistant:", style="green bold")
                console.print(Markdown(rendered_text))
                console.print()  # Add spacing after response

            except Exception as e:
                console.print(f"\n[bold red]Error:[/] {str(e)}\n")


if __name__ == "__main__":
    chat_cli()
