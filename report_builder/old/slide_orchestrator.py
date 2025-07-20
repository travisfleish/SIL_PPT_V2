# report_builder/slide_orchestrator.py
"""
Slide orchestrator that manages the workflow and dependencies
between different slide generators
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import traceback

logger = logging.getLogger(__name__)


class SlideStatus(Enum):
    """Status of slide generation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SlideTask:
    """Represents a slide generation task"""
    name: str
    slide_type: str
    generator_func: Callable
    dependencies: List[str] = None
    required_data: List[str] = None
    status: SlideStatus = SlideStatus.PENDING
    error_message: Optional[str] = None
    result: Optional[Any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.required_data is None:
            self.required_data = []


class SlideOrchestrator:
    """Orchestrates the slide generation workflow"""

    def __init__(self):
        """Initialize the orchestrator"""
        self.tasks: Dict[str, SlideTask] = {}
        self.data_cache: Dict[str, Any] = {}
        self.completed_slides: List[str] = []
        self.failed_slides: List[str] = []

    def register_task(self, task: SlideTask):
        """Register a slide generation task"""
        self.tasks[task.name] = task
        logger.info(f"Registered task: {task.name}")

    def add_data(self, key: str, data: Any):
        """Add data to the cache for use by slide generators"""
        self.data_cache[key] = data
        logger.info(f"Added data: {key}")

    def can_execute_task(self, task_name: str) -> bool:
        """Check if a task can be executed based on dependencies"""
        task = self.tasks.get(task_name)
        if not task:
            return False

        # Check if all dependencies are completed
        for dep in task.dependencies:
            dep_task = self.tasks.get(dep)
            if not dep_task or dep_task.status != SlideStatus.COMPLETED:
                return False

        # Check if all required data is available
        for data_key in task.required_data:
            if data_key not in self.data_cache:
                logger.warning(f"Missing required data: {data_key} for task {task_name}")
                return False

        return True

    def execute_task(self, task_name: str) -> bool:
        """Execute a specific task"""
        task = self.tasks.get(task_name)
        if not task:
            logger.error(f"Task not found: {task_name}")
            return False

        if task.status == SlideStatus.COMPLETED:
            logger.info(f"Task already completed: {task_name}")
            return True

        if not self.can_execute_task(task_name):
            logger.warning(f"Cannot execute task yet: {task_name}")
            return False

        logger.info(f"Executing task: {task_name}")
        task.status = SlideStatus.IN_PROGRESS

        try:
            # Prepare arguments for the generator function
            kwargs = {}
            for data_key in task.required_data:
                kwargs[data_key] = self.data_cache[data_key]

            # Execute the generator function
            result = task.generator_func(**kwargs)

            task.result = result
            task.status = SlideStatus.COMPLETED
            self.completed_slides.append(task_name)

            logger.info(f"✓ Task completed: {task_name}")
            return True

        except Exception as e:
            task.status = SlideStatus.FAILED
            task.error_message = str(e)
            self.failed_slides.append(task_name)

            logger.error(f"✗ Task failed: {task_name}")
            logger.error(f"Error: {str(e)}")
            logger.error(traceback.format_exc())

            return False

    def execute_all(self, skip_on_failure: bool = True) -> Dict[str, Any]:
        """
        Execute all registered tasks in dependency order

        Args:
            skip_on_failure: Whether to continue with other tasks if one fails

        Returns:
            Execution summary
        """
        logger.info("Starting slide generation workflow...")

        # Keep trying to execute tasks until no more progress can be made
        max_iterations = len(self.tasks) * 2  # Safety limit
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            progress_made = False

            for task_name, task in self.tasks.items():
                if task.status == SlideStatus.PENDING:
                    if self.execute_task(task_name):
                        progress_made = True
                    elif not skip_on_failure and task.status == SlideStatus.FAILED:
                        logger.error("Stopping execution due to failure")
                        break

            if not progress_made:
                break

        # Mark remaining tasks as skipped
        for task_name, task in self.tasks.items():
            if task.status == SlideStatus.PENDING:
                task.status = SlideStatus.SKIPPED
                logger.warning(f"Task skipped: {task_name}")

        return self.get_summary()

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary"""
        summary = {
            'total_tasks': len(self.tasks),
            'completed': len(self.completed_slides),
            'failed': len(self.failed_slides),
            'skipped': len([t for t in self.tasks.values() if t.status == SlideStatus.SKIPPED]),
            'completed_slides': self.completed_slides,
            'failed_slides': self.failed_slides,
            'task_details': {}
        }

        for task_name, task in self.tasks.items():
            summary['task_details'][task_name] = {
                'status': task.status.value,
                'error': task.error_message,
                'slide_type': task.slide_type
            }

        return summary

    def reset(self):
        """Reset the orchestrator for a new run"""
        for task in self.tasks.values():
            task.status = SlideStatus.PENDING
            task.error_message = None
            task.result = None

        self.completed_slides = []
        self.failed_slides = []
        logger.info("Orchestrator reset")


class CategorySlideOrchestrator:
    """Specialized orchestrator for handling multiple category slides"""

    def __init__(self, base_orchestrator: SlideOrchestrator):
        """
        Initialize category slide orchestrator

        Args:
            base_orchestrator: The main slide orchestrator
        """
        self.base_orchestrator = base_orchestrator
        self.category_tasks = []

    def register_category_slides(self,
                                 categories: List[str],
                                 generator_func: Callable,
                                 is_custom: bool = False):
        """
        Register multiple category slide tasks

        Args:
            categories: List of category names/keys
            generator_func: Function to generate category slides
            is_custom: Whether these are custom categories
        """
        for i, category in enumerate(categories):
            task_name = f"category_{category}" if not is_custom else f"custom_category_{i + 1}"

            # Create a wrapped generator function for this specific category
            def make_generator(cat_name, custom_flag):
                def generator(**kwargs):
                    return generator_func(
                        category_key=cat_name,
                        is_custom=custom_flag,
                        **kwargs
                    )

                return generator

            task = SlideTask(
                name=task_name,
                slide_type="category",
                generator_func=make_generator(category, is_custom),
                dependencies=["behaviors"],  # Categories come after behaviors
                required_data=["presentation", "category_analyzer", "team_config"]
            )

            self.base_orchestrator.register_task(task)
            self.category_tasks.append(task_name)

        logger.info(f"Registered {len(categories)} {'custom' if is_custom else 'fixed'} category tasks")


def create_standard_workflow() -> SlideOrchestrator:
    """
    Create the standard slide generation workflow

    Returns:
        Configured SlideOrchestrator
    """
    orchestrator = SlideOrchestrator()

    # Define the standard slide generation tasks

    # Title slide - no dependencies
    orchestrator.register_task(SlideTask(
        name="title",
        slide_type="title",
        generator_func=lambda **kwargs: None,  # Placeholder
        dependencies=[],
        required_data=["presentation", "team_config"]
    ))

    # Demographics slide - depends on title
    orchestrator.register_task(SlideTask(
        name="demographics",
        slide_type="demographics",
        generator_func=lambda **kwargs: None,  # Placeholder
        dependencies=["title"],
        required_data=["presentation", "demographic_data", "team_config"]
    ))

    # Behaviors slide - depends on demographics
    orchestrator.register_task(SlideTask(
        name="behaviors",
        slide_type="behaviors",
        generator_func=lambda **kwargs: None,  # Placeholder
        dependencies=["demographics"],
        required_data=["presentation", "merchant_ranker", "team_config"]
    ))

    return orchestrator