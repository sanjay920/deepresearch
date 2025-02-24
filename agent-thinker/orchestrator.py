import logging
from typing import List, Dict, Any, Callable
from collections import deque
from retrieval import RetrievalAgent
from synthesis import SynthesisAgent
from validation import ValidationAgent
import json


class Task:
    """Represents a single task with type, parameters, status, and dependencies."""

    def __init__(
        self,
        task_id: str,
        task_type: str,
        params: Dict[str, Any],
        dependencies: List[str] = None,
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.params = params
        self.dependencies = dependencies or []
        self.status = "pending"  # pending, in_progress, completed, failed
        self.result = None

    def get_description(self):
        """Return a user-friendly description of the task."""
        if self.task_type == "retrieval":
            if "query" in self.params:
                return f"Searching for '{self.params['query']}'"
            elif "url" in self.params:
                return f"Retrieving content from {self.params['url']}"
        elif self.task_type == "synthesis":
            return "Generating summary"
        elif self.task_type == "validation":
            return "Validating results for citation presence"
        return "Unknown task"


class Orchestrator:
    """Manages the task queue and coordinates task execution."""

    def __init__(self):
        self.task_queue = deque()
        self.tasks: Dict[str, Task] = {}
        self.agents = {
            "retrieval": RetrievalAgent(),
            "synthesis": SynthesisAgent(),
            "validation": ValidationAgent(),
        }
        self.synthesis_iteration = 0  # Track synthesis iterations

    def add_task(self, task: Task):
        """Add a task to the queue and the tasks dictionary."""
        self.task_queue.append(task)
        self.tasks[task.task_id] = task
        logging.info(f"Added task: {task.get_description()}")

    def execute_tasks(self, on_task_start: Callable[[Task], None] = None):
        """Execute tasks in the queue, respecting dependencies."""
        while self.task_queue:
            task = self.task_queue.popleft()
            if self.can_execute(task):
                if on_task_start:
                    on_task_start(task)
                self.execute_task(task)

                # Handle synthesis task result
                if task.task_type == "synthesis" and task.status == "completed":
                    try:
                        synthesis_output = json.loads(task.result)
                        if (
                            synthesis_output["status"] == "incomplete"
                            and self.synthesis_iteration < 8
                        ):
                            # Queue additional tasks from the synthesis output
                            if "additional_tasks" in synthesis_output and isinstance(
                                synthesis_output["additional_tasks"], list
                            ):
                                for additional_task in synthesis_output[
                                    "additional_tasks"
                                ]:
                                    if not isinstance(additional_task, dict):
                                        continue

                                    tool = additional_task.get("tool")
                                    parameters = additional_task.get("parameters", {})

                                    if tool == "scrape_urls" and "urls" in parameters:
                                        for url in parameters["urls"]:
                                            new_task_id = (
                                                f"retrieval_url_{len(self.tasks)}"
                                            )
                                            new_task = Task(
                                                task_id=new_task_id,
                                                task_type="retrieval",
                                                params={"url": url},
                                            )
                                            self.add_task(new_task)
                                    elif tool == "google_search" and "q" in parameters:
                                        new_task_id = (
                                            f"retrieval_search_{len(self.tasks)}"
                                        )
                                        new_task = Task(
                                            task_id=new_task_id,
                                            task_type="retrieval",
                                            params={"query": parameters["q"]},
                                        )
                                        self.add_task(new_task)

                            # Queue new synthesis task
                            all_retrieval_ids = [
                                t.task_id
                                for t in self.tasks.values()
                                if t.task_type == "retrieval"
                            ]
                            new_synthesis_task = Task(
                                task_id=f"synthesis_{len(self.tasks)}",
                                task_type="synthesis",
                                params={"query": task.params["query"]},
                                dependencies=all_retrieval_ids,
                            )
                            self.add_task(new_synthesis_task)
                    except json.JSONDecodeError as e:
                        logging.error(f"Synthesis output is not valid JSON: {e}")
                        task.status = "failed"
                        task.result = "[Error: Invalid synthesis output format]"
            else:
                # Re-add to the end of the queue if dependencies are not met
                self.task_queue.append(task)

    def can_execute(self, task: Task) -> bool:
        """Check if all dependencies of the task are completed."""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != "completed":
                return False
        return True

    def execute_task(self, task: Task):
        """Execute the task using the appropriate agent."""
        task.status = "in_progress"
        logging.info(f"Executing task: {task.get_description()}")

        try:
            agent = self.agents.get(task.task_type)
            if not agent:
                raise ValueError(f"No agent found for task type {task.task_type}")

            if task.task_type == "retrieval":
                if "query" in task.params:
                    result = agent.search(task.params["query"])
                    task.result = {
                        "type": "search",
                        "query": task.params["query"],
                        "results": result,
                    }
                elif "url" in task.params:
                    result = agent.retrieve_webpage(task.params["url"])
                    task.result = {
                        "type": "scrape",
                        "url": task.params["url"],
                        "content": result,
                    }
                else:
                    raise ValueError("Invalid retrieval parameters")

            elif task.task_type == "synthesis":
                retrieval_results = [
                    self.tasks[dep_id].result
                    for dep_id in task.dependencies
                    if self.tasks[dep_id].status == "completed"
                ]
                self.synthesis_iteration += 1
                result = agent.synthesize(
                    task.params["query"], retrieval_results, self.synthesis_iteration
                )
                task.result = result

            elif task.task_type == "validation":
                synthesis_task = self.tasks[task.params["synthesis_task_id"]]
                synthesis_result = json.loads(synthesis_task.result)
                summary = synthesis_result.get("summary", "")
                result = agent.validate(summary, "")
                task.result = result

            else:
                raise ValueError(f"Unsupported task type: {task.task_type}")

            task.status = "completed"
            logging.info(f"Task completed: {task.get_description()}")

        except Exception as e:
            task.result = f"[Error: {str(e)}]"
            task.status = "failed"
            logging.error(f"Task failed: {task.get_description()} - {e}")

    def get_pending_tasks(self):
        """Return a list of tasks still in the queue."""
        return list(self.task_queue)

    def get_completed_tasks(self):
        """Return a list of completed tasks."""
        return [task for task in self.tasks.values() if task.status == "completed"]
