# utils/team_config_manager.py
import yaml
from pathlib import Path
from typing import Dict, Any


class TeamConfigManager:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'team_config.yaml'

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.view_patterns = self.config['view_patterns']
        self.teams = self.config['teams']

    def get_team_config(self, team_key: str) -> Dict[str, Any]:
        """Get full configuration for a team"""
        if team_key not in self.teams:
            raise ValueError(f"Team '{team_key}' not found in configuration")
        return self.teams[team_key]

    def get_view_name(self, team_key: str, view_type: str) -> str:
        """
        Get the full view name for a team and view type

        Args:
            team_key: e.g., 'utah_jazz', 'dallas_cowboys'
            view_type: e.g., 'community_all_time', 'merchant_yoy', 'demographics'

        Returns:
            Full view name, e.g., 'V_UTAH_JAZZ_SIL_DEMOGRAPHICS_DIST'
        """
        team_config = self.get_team_config(team_key)
        prefix = team_config['view_prefix']

        if view_type not in self.view_patterns:
            raise ValueError(f"View type '{view_type}' not found in patterns")

        pattern = self.view_patterns[view_type]
        view_name = pattern.format(prefix=prefix)

        # Special case handling removed - Utah Jazz now uses standard pattern
        # This will resolve to: V_UTAH_JAZZ_SIL_DEMOGRAPHICS_DIST

        return view_name

    def get_all_views_for_team(self, team_key: str) -> Dict[str, str]:
        """Get all view names for a team"""
        team_config = self.get_team_config(team_key)
        prefix = team_config['view_prefix']

        views = {}
        for view_type, pattern in self.view_patterns.items():
            view_name = pattern.format(prefix=prefix)

            # Special case handling removed - Utah Jazz now uses standard pattern
            # This will resolve to: V_UTAH_JAZZ_SIL_DEMOGRAPHICS_DIST

            views[view_type] = view_name

        return views

    def list_teams(self) -> list:
        """List all available team keys"""
        return list(self.teams.keys())


# Example usage and validation:
if __name__ == "__main__":
    manager = TeamConfigManager()

    # Test both teams
    print("Utah Jazz views:")
    jazz_views = manager.get_all_views_for_team('utah_jazz')
    print(f"  Community: {jazz_views['community_all_time']}")
    print(f"  Demographics: {jazz_views['demographics']}")
    print(f"  Expected: V_UTAH_JAZZ_SIL_DEMOGRAPHICS_DIST")

    print("\nDallas Cowboys views:")
    cowboys_views = manager.get_all_views_for_team('dallas_cowboys')
    print(f"  Community: {cowboys_views['community_all_time']}")
    print(f"  Demographics: {cowboys_views['demographics']}")
    print(f"  Expected: V_DALLAS_COWBOYS_DEMOGRAPHICS_DIST")

    # Validate Utah Jazz demographics specifically
    utah_demographics = manager.get_view_name('utah_jazz', 'demographics')
    assert utah_demographics == 'V_UTAH_JAZZ_SIL_DEMOGRAPHICS_DIST', f"Expected V_UTAH_JAZZ_SIL_DEMOGRAPHICS_DIST, got {utah_demographics}"
    print(f"\n✅ Utah Jazz demographics view correct: {utah_demographics}")

    # Validate Dallas Cowboys demographics specifically
    cowboys_demographics = manager.get_view_name('dallas_cowboys', 'demographics')
    assert cowboys_demographics == 'V_DALLAS_COWBOYS_DEMOGRAPHICS_DIST', f"Expected V_DALLAS_COWBOYS_DEMOGRAPHICS_DIST, got {cowboys_demographics}"
    print(f"✅ Dallas Cowboys demographics view correct: {cowboys_demographics}")