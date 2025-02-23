import logging
from typing import List, Dict, Any
from collections import deque
from retrieval import RetrievalAgent
from synthesis import SynthesisAgent
from validation import ValidationAgent


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

    def add_task(self, task: Task):
        """Add a task to the queue and the tasks dictionary."""
        self.task_queue.append(task)
        self.tasks[task.task_id] = task
        logging.info(f"Added task {task.task_id} of type {task.task_type}")

    def execute_tasks(self):
        """Execute tasks in the queue, respecting dependencies."""
        while self.task_queue:
            task = self.task_queue.popleft()
            if self.can_execute(task):
                self.execute_task(task)
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
        logging.info(f"Executing task {task.task_id} of type {task.task_type}")
        try:
            agent = self.agents.get(task.task_type)
            if not agent:
                raise ValueError(f"No agent found for task type {task.task_type}")
            if task.task_type == "retrieval":
                if "query" in task.params:
                    result = agent.search(task.params["query"])
                elif "url" in task.params:
                    result = agent.retrieve_webpage(task.params["url"])
                else:
                    raise ValueError("Invalid parameters for retrieval task")
            elif task.task_type == "synthesis":
                result = agent.synthesize(task.params["query"], task.params["data"])
            elif task.task_type == "validation":
                result = agent.validate(task.params["summary"], task.params["sources"])
            else:
                raise ValueError(f"Unsupported task type: {task.task_type}")
            task.result = result
            task.status = "completed"
            logging.info(f"Task {task.task_id} completed successfully")
        except Exception as e:
            task.status = "failed"
            logging.error(f"Task {task.task_id} failed: {e}")

    def get_task_results(self) -> Dict[str, Any]:
        """Return the results of all completed tasks."""
        return {
            task_id: task.result
            for task_id, task in self.tasks.items()
            if task.status == "completed"
        }
