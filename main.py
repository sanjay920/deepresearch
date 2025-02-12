import click
import requests
import json

# You can set these to the actual ports your containers expose.
ROUTER_BASE_URL = "http://localhost:8082"
PLANNING_BASE_URL = "http://localhost:8083"
SOLVER_BASE_URL = "http://localhost:8086"

# Service timeouts (in seconds)
ROUTER_TIMEOUT = 120
PLANNING_TIMEOUT = 120
SOLVER_TIMEOUT = 3600  # Increased timeout for solver since it handles complex tasks


def call_router_service(message: str) -> dict:
    """
    Calls the router microservice with the provided message.
    Returns a dict following the spec:
      {
        "is_complex": bool,
        "response": <string>   (if is_complex=False),
        "pass": <bool>         (possible),
        ...
      }
    """
    url = f"{ROUTER_BASE_URL}/route"
    payload = {"message": message}
    try:
        resp = requests.post(url, json=payload, timeout=ROUTER_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        click.secho(f"[Error] Router service request failed: {e}", fg="red")
        return {}


def call_planning_assistant(message: str, conversation_history=None) -> dict:
    """
    Calls the planning assistant microservice. Expects:
      {
        "message": <str>,
        "conversation_history": [ { "role":"...", "content":"..." }, ... ]
      }
    Returns a JSON dict with keys: "objective", "research_plan", "clarifications", etc.
    """
    url = f"{PLANNING_BASE_URL.rstrip('/')}/generate"
    payload = {
        "message": message,
        "conversation_history": conversation_history if conversation_history else [],
    }
    try:
        resp = requests.post(url, json=payload, timeout=PLANNING_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        click.secho(f"[Error] Planning assistant request failed: {e}", fg="red")
        return {}


def call_solver_service(objective: str, research_plan: list) -> str:
    """
    Calls the solver microservice with the provided objective and research plan.
    Returns the solver's final string response (Markdown, etc.), or empty if fail.
    """
    url = f"{SOLVER_BASE_URL.rstrip('/')}/solve"
    payload = {"objective": objective, "research_plan": research_plan}
    try:
        resp = requests.post(
            url, json=payload, timeout=SOLVER_TIMEOUT
        )  # Increased timeout
        resp.raise_for_status()
        return resp.json()  # Typically returns a string
    except requests.exceptions.RequestException as e:
        click.secho(f"[Error] Solver service request failed: {e}", fg="red")
        return ""


def collect_user_message() -> str:
    """
    Collect multi-line input from the user until a line containing only a period "."
    is entered to indicate completion.
    """
    click.secho(
        "Enter your message. When finished, type '.' on a new line to submit.",
        fg="cyan",
    )
    lines = []
    while True:
        line = input()  # Normal input for each line
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines)


@click.command()
def cli():
    """
    Example CLI that orchestrates:
      1. Router -> decides is_complex?
      2. If simple, returns a direct answer (now storing context)
      3. If complex or if a refinement is detected, calls Planning Assistant
         (with clarifications if needed) and then the Solver.
    """
    click.secho(
        "Welcome to the multi-service CLI! Type 'exit' or 'quit' to stop.", fg="cyan"
    )
    conversation_history = []  # This will store all user & assistant messages

    # Helper function to detect refinement requests based on simple heuristics.
    def is_refinement(message: str) -> bool:
        lower = message.lower()
        return (
            ("good" in lower and "but" in lower)
            or ("instead" in lower)
            or ("change" in lower)
            or ("format" in lower)
        )

    while True:
        user_input = collect_user_message().strip()
        if user_input.lower() in ("exit", "quit"):
            click.secho("Goodbye!", fg="cyan")
            break

        # Always add the user message to the conversation history.
        conversation_history.append({"role": "user", "content": user_input})

        # If there is context from a previous exchange and the user input appears to be a refinement,
        # then handle it via the planning assistant branch.
        if len(conversation_history) > 1 and is_refinement(user_input):
            click.secho(
                "Detected refinement request. Processing with Planning Assistant...",
                fg="yellow",
            )
            planning_result = call_planning_assistant(user_input, conversation_history)
            conversation_history.append(
                {"role": "assistant", "content": json.dumps(planning_result)}
            )
            clarifications = planning_result.get("clarifications", [])
            while clarifications:
                click.secho(
                    "\nThe Planning Assistant needs more details:", fg="magenta"
                )
                for c in clarifications:
                    click.secho(f" - {c}", fg="magenta")
                clarification_reply = collect_user_message().strip()
                conversation_history.append(
                    {"role": "user", "content": clarification_reply}
                )
                planning_result = call_planning_assistant(
                    clarification_reply, conversation_history
                )
                conversation_history.append(
                    {"role": "assistant", "content": json.dumps(planning_result)}
                )
                clarifications = planning_result.get("clarifications", [])
            objective = planning_result.get("objective", "")
            research_plan = planning_result.get("research_plan", [])
            click.secho(
                f"\nExecuting the plan with the Solver:\nObjective: {objective}\nPlan: {research_plan}",
                fg="yellow",
            )
            solver_output = call_solver_service(objective, research_plan)
            if solver_output:
                click.secho("\n--- SOLVER OUTPUT ---", fg="green")
                click.echo(solver_output)
                click.secho("--- END ---", fg="green")
            else:
                click.secho("Solver returned no output or error.", fg="red")
            continue

        # Normal processing through the Router service.
        router_result = call_router_service(user_input)
        if not router_result:
            continue

        if router_result.get("is_complex") is False:
            if router_result.get("pass"):
                click.secho(
                    "Router indicated pass=true, it used the tool's final answer behind the scenes.",
                    fg="yellow",
                )
            else:
                answer = router_result.get("response", "(No 'response' key found.)")
                conversation_history.append({"role": "assistant", "content": answer})
                click.secho(f"Answer: {answer}", fg="green")
            continue

        # For complex queries, call the Planning Assistant.
        click.secho(
            "Router says it's COMPLEX. Calling Planning Assistant...", fg="yellow"
        )
        planning_result = call_planning_assistant(user_input, conversation_history)
        conversation_history.append(
            {"role": "assistant", "content": json.dumps(planning_result)}
        )
        clarifications = planning_result.get("clarifications", [])
        while clarifications:
            click.secho("\nThe Planning Assistant needs more details:", fg="magenta")
            for c in clarifications:
                click.secho(f" - {c}", fg="magenta")
            clarification_reply = collect_user_message().strip()
            conversation_history.append(
                {"role": "user", "content": clarification_reply}
            )
            planning_result = call_planning_assistant(
                clarification_reply, conversation_history
            )
            conversation_history.append(
                {"role": "assistant", "content": json.dumps(planning_result)}
            )
            clarifications = planning_result.get("clarifications", [])
        objective = planning_result.get("objective", "")
        research_plan = planning_result.get("research_plan", [])
        click.secho(
            f"\nExecuting the plan with the Solver:\nObjective: {objective}\nPlan: {research_plan}",
            fg="yellow",
        )
        solver_output = call_solver_service(objective, research_plan)
        if solver_output:
            click.secho("\n--- SOLVER OUTPUT ---", fg="green")
            click.echo(solver_output)
            click.secho("--- END ---", fg="green")
        else:
            click.secho("Solver returned no output or error.", fg="red")


if __name__ == "__main__":
    cli()
