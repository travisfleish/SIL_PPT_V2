"""
PowerPoint generation service with progress tracking
Wraps the existing PowerPointBuilder with progress callbacks
"""

import sys
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from contextlib import contextmanager
import time

# Add parent directory to import existing modules
sys.path.append(str(Path(__file__).parent.parent))

from report_builder.pptx_builder import PowerPointBuilder as OriginalBuilder
from slide_generators.title_slide import TitleSlide
from slide_generators.demographics_slide import DemographicsSlide
from slide_generators.behaviors_slide import BehaviorsSlide
from slide_generators.category_slide import CategorySlide


class ProgressTracker:
    """Tracks progress across multiple stages of generation"""

    def __init__(self, callback: Callable[[int, str], None]):
        self.callback = callback
        self.stages = {
            'initialization': (0, 5),
            'connection': (5, 10),
            'data_loading': (10, 20),
            'demographics': (20, 30),
            'behaviors': (30, 40),
            'categories': (40, 90),
            'finalization': (90, 100)
        }
        self.current_stage = 'initialization'
        self.category_count = 10  # Will be updated

    def update_stage(self, stage: str, sub_progress: float = 0.0):
        """Update progress for a specific stage"""
        if stage in self.stages:
            self.current_stage = stage
            start, end = self.stages[stage]
            progress = int(start + (end - start) * sub_progress)
            self.callback(progress, self._get_stage_message(stage))

    def update_category_progress(self, current: int, total: int):
        """Special handling for category progress"""
        sub_progress = current / total if total > 0 else 0
        self.update_stage('categories', sub_progress)

    def _get_stage_message(self, stage: str) -> str:
        """Get user-friendly message for each stage"""
        messages = {
            'initialization': 'Initializing PowerPoint builder...',
            'connection': 'Connecting to database...',
            'data_loading': 'Loading team data from Snowflake...',
            'demographics': 'Generating demographics analysis...',
            'behaviors': 'Creating fan behavior visualizations...',
            'categories': 'Analyzing spending categories...',
            'finalization': 'Finalizing presentation...'
        }
        return messages.get(stage, f'Processing {stage}...')


class PowerPointBuilderWithProgress(OriginalBuilder):
    """Extended PowerPointBuilder with progress tracking"""

    def __init__(self, team_key: str, progress_callback: Optional[Callable] = None):
        super().__init__(team_key)
        self.progress_callback = progress_callback or (lambda p, m: None)
        self.tracker = ProgressTracker(self.progress_callback)

    @contextmanager
    def _track_stage(self, stage: str):
        """Context manager to track stage progress"""
        self.tracker.update_stage(stage, 0.0)
        yield
        self.tracker.update_stage(stage, 1.0)

    def build_presentation(self,
                           include_custom_categories: bool = True,
                           custom_category_count: Optional[int] = None) -> Path:
        """Build presentation with progress tracking"""

        # Initialize
        with self._track_stage('initialization'):
            # Original initialization code
            time.sleep(0.5)  # Simulate work

        # Test connection
        with self._track_stage('connection'):
            # Connection test
            time.sleep(0.5)

        # Data loading
        with self._track_stage('data_loading'):
            # Would normally load all data here
            time.sleep(1)

        # Create presentation
        try:
            # Title slide
            self.tracker.update_stage('initialization', 0.8)
            self._add_title_slide()

            # Demographics
            with self._track_stage('demographics'):
                self._add_demographics_slide()

            # Behaviors
            with self._track_stage('behaviors'):
                self._add_behaviors_slide()

            # Categories
            categories = self._get_categories_to_process(include_custom_categories, custom_category_count)
            total_categories = len(categories)

            for idx, category in enumerate(categories):
                self.tracker.update_category_progress(idx, total_categories)
                self._add_category_slide(category)

            # Finalize
            with self._track_stage('finalization'):
                output_path = self._save_presentation()

            return output_path

        except Exception as e:
            self.progress_callback(0, f'Error: {str(e)}')
            raise

    def _add_title_slide(self):
        """Add title slide with progress tracking"""
        # Wrap original method
        super()._add_title_slide() if hasattr(super(), '_add_title_slide') else None

    def _add_demographics_slide(self):
        """Add demographics slide with progress tracking"""
        # Implementation would call original demographics logic
        time.sleep(1)  # Simulate processing

    def _add_behaviors_slide(self):
        """Add behaviors slide with progress tracking"""
        # Implementation would call original behaviors logic
        time.sleep(1)  # Simulate processing

    def _add_category_slide(self, category: str):
        """Add category slide with progress tracking"""
        # Implementation would call original category logic
        time.sleep(0.5)  # Simulate processing

    def _get_categories_to_process(self, include_custom: bool, custom_count: Optional[int]) -> list:
        """Get list of categories to process"""
        # Fixed categories
        fixed_categories = [
            'restaurants',
            'athleisure',
            'finance',
            'gambling',
            'travel',
            'auto'
        ]

        if not include_custom:
            return fixed_categories

        # Add custom categories (mock)
        custom_categories = [f'custom_{i}' for i in range(custom_count or 4)]

        return fixed_categories + custom_categories

    def _save_presentation(self) -> Path:
        """Save the presentation"""
        # Mock implementation
        output_file = self.output_dir / f"{self.team_key}_sponsorship_insights_{self.timestamp}.pptx"

        # Would normally save the actual presentation
        output_file.touch()  # Create empty file for testing

        return output_file


def create_progress_callback(job_id: str, update_func: Callable) -> Callable:
    """Create a progress callback function for a specific job"""

    def callback(progress: int, message: str):
        """Update job progress"""
        update_func(job_id, progress=progress, message=message)

    return callback


# Convenience function for testing
def generate_with_progress(team_key: str,
                           progress_callback: Callable,
                           **options) -> Path:
    """Generate PowerPoint with progress tracking"""

    builder = PowerPointBuilderWithProgress(team_key, progress_callback)

    return builder.build_presentation(
        include_custom_categories=not options.get('skip_custom', False),
        custom_category_count=options.get('custom_count')
    )