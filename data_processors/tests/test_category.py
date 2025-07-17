"""
Category Selection Diagnostic Script
Analyzes which categories are selected for custom categories and why
Shows the full filtering process step by step
"""

import pandas as pd
import yaml
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class CategoryDiagnostic:
    """Diagnostic tool for understanding category selection"""

    def __init__(self, config_path: Path = None):
        """Initialize with config"""
        if config_path is None:
            config_path = Path('config/categories.yaml')

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.categories = self.config['categories']
        self.excluded_custom = self.config['excluded_from_custom']
        self.allowed_custom = self.config.get('allowed_for_custom', [])
        self.fixed_categories = self.config['fixed_categories']

    def analyze_category_selection(self,
                                   category_df: pd.DataFrame,
                                   team_name: str,
                                   team_short: str,
                                   is_womens_team: bool = False) -> Dict[str, any]:
        """
        Analyze the category selection process step by step

        Args:
            category_df: DataFrame from CATEGORY_INDEXING_ALL_TIME view
            team_name: Full team name (e.g., "Utah Jazz")
            team_short: Short team name (e.g., "Jazz")
            is_womens_team: Whether this is a women's team

        Returns:
            Dictionary with diagnostic information
        """
        audience_name = f"{team_name} Fans"
        comparison_pop = f"Local Gen Pop (Excl. {team_short})"

        # Get config
        custom_config = self.config.get('custom_category_config', {})
        n_categories = (custom_config.get('womens_teams', {}).get('count', 2) if is_womens_team
                        else custom_config.get('mens_teams', {}).get('count', 4))
        min_audience = custom_config.get('min_audience_pct', 0.20)

        # Get fixed categories being used
        fixed_cat_keys = (self.fixed_categories['womens_teams'] if is_womens_team
                          else self.fixed_categories['mens_teams'])

        # Get category names from fixed categories
        category_names_from_fixed = []
        for cat_key in fixed_cat_keys:
            if cat_key in self.categories:
                category_names_from_fixed.extend(
                    self.categories[cat_key].get('category_names_in_data', [])
                )

        # Step 1: Get all team data
        all_team_data = category_df[category_df['AUDIENCE'] == audience_name].copy()

        # Step 2: Filter by audience threshold
        audience_filtered = all_team_data[
            all_team_data['PERC_AUDIENCE'] >= min_audience
        ].copy()

        # Step 3: Apply allowed list filter (if exists)
        if self.allowed_custom:
            allowed_filtered = audience_filtered[
                audience_filtered['CATEGORY'].isin(self.allowed_custom)
            ].copy()
        else:
            allowed_filtered = audience_filtered.copy()

        # Step 4: Apply excluded list filter
        excluded_filtered = allowed_filtered[
            ~allowed_filtered['CATEGORY'].isin(self.excluded_custom)
        ].copy()

        # Step 5: Remove fixed categories
        final_filtered = excluded_filtered[
            ~excluded_filtered['CATEGORY'].isin(category_names_from_fixed)
        ].copy()

        # Step 6: Get top N by composite index
        top_categories = final_filtered.nlargest(n_categories, 'COMPOSITE_INDEX')

        # Create diagnostic report
        diagnostic = {
            'team_info': {
                'team_name': team_name,
                'is_womens_team': is_womens_team,
                'target_custom_categories': n_categories,
                'min_audience_pct': min_audience
            },
            'fixed_categories': {
                'keys_used': fixed_cat_keys,
                'category_names_in_data': category_names_from_fixed
            },
            'filtering_steps': {
                'step1_all_team_data': self._summarize_dataframe(all_team_data),
                'step2_audience_filtered': self._summarize_dataframe(audience_filtered),
                'step3_allowed_filtered': self._summarize_dataframe(allowed_filtered),
                'step4_excluded_filtered': self._summarize_dataframe(excluded_filtered),
                'step5_final_filtered': self._summarize_dataframe(final_filtered),
                'step6_top_selected': self._summarize_dataframe(top_categories)
            },
            'filter_lists': {
                'allowed_custom': self.allowed_custom,
                'excluded_custom': self.excluded_custom
            },
            'categories_removed_at_each_step': {
                'removed_by_audience': self._get_removed_categories(all_team_data, audience_filtered),
                'removed_by_allowed': self._get_removed_categories(audience_filtered, allowed_filtered),
                'removed_by_excluded': self._get_removed_categories(allowed_filtered, excluded_filtered),
                'removed_by_fixed': self._get_removed_categories(excluded_filtered, final_filtered)
            },
            'final_selection': self._get_final_selection_details(top_categories)
        }

        return diagnostic

    def _summarize_dataframe(self, df: pd.DataFrame) -> Dict[str, any]:
        """Summarize a dataframe for diagnostic purposes"""
        if df.empty:
            return {
                'count': 0,
                'categories': []
            }

        # Sort by composite index for better visibility
        df_sorted = df.sort_values('COMPOSITE_INDEX', ascending=False)

        return {
            'count': len(df),
            'categories': df_sorted[['CATEGORY', 'COMPOSITE_INDEX', 'PERC_AUDIENCE']].to_dict('records')
        }

    def _get_removed_categories(self, before_df: pd.DataFrame, after_df: pd.DataFrame) -> List[str]:
        """Get categories that were removed in a filtering step"""
        before_cats = set(before_df['CATEGORY'].unique()) if not before_df.empty else set()
        after_cats = set(after_df['CATEGORY'].unique()) if not after_df.empty else set()
        return sorted(list(before_cats - after_cats))

    def _get_final_selection_details(self, top_categories: pd.DataFrame) -> List[Dict[str, any]]:
        """Get detailed info about final selected categories"""
        if top_categories.empty:
            return []

        details = []
        for idx, (_, row) in enumerate(top_categories.iterrows(), 1):
            details.append({
                'rank': idx,
                'category': row['CATEGORY'],
                'composite_index': float(row['COMPOSITE_INDEX']),
                'perc_audience': float(row['PERC_AUDIENCE']),
                'perc_index': float(row['PERC_INDEX']),
                'would_be_slide_title': f"{row['CATEGORY']} Sponsor Analysis"
            })

        return details

    def print_diagnostic_report(self, diagnostic: Dict[str, any]):
        """Print a formatted diagnostic report"""
        print("\n" + "="*80)
        print("CATEGORY SELECTION DIAGNOSTIC REPORT")
        print("="*80)

        # Team info
        print("\n📋 TEAM INFORMATION:")
        info = diagnostic['team_info']
        print(f"  Team: {info['team_name']}")
        print(f"  Type: {'Womens' if info['is_womens_team'] else 'Mens'} Team")
        print(f"  Target Custom Categories: {info['target_custom_categories']}")
        print(f"  Min Audience %: {info['min_audience_pct']*100:.0f}%")

        # Fixed categories
        print("\n📌 FIXED CATEGORIES IN USE:")
        fixed = diagnostic['fixed_categories']
        print(f"  Category Keys: {', '.join(fixed['keys_used'])}")
        print(f"  Data Names: {', '.join(fixed['category_names_in_data'])}")

        # Filtering process
        print("\n🔍 FILTERING PROCESS:")
        steps = diagnostic['filtering_steps']

        for step_name, step_data in steps.items():
            step_display = step_name.replace('_', ' ').title()
            print(f"\n  {step_display}: {step_data['count']} categories")

            if step_data['count'] > 0 and step_data['count'] <= 15:
                # Show all categories if 15 or fewer
                print(f"    {'Category':<40} {'Composite Index':>15} {'Audience %':>12}")
                print(f"    {'-'*40} {'-'*15} {'-'*12}")
                for cat in step_data['categories']:
                    cat_name = cat['CATEGORY'][:38] + '..' if len(cat['CATEGORY']) > 40 else cat['CATEGORY']
                    comp_idx = cat['COMPOSITE_INDEX']
                    aud_pct = cat['PERC_AUDIENCE'] * 100
                    print(f"    {cat_name:<40} {comp_idx:>15.1f} {aud_pct:>12.1f}")

        # Categories removed at each step
        print("\n❌ CATEGORIES REMOVED AT EACH STEP:")
        removed = diagnostic['categories_removed_at_each_step']
        for step, cats in removed.items():
            if cats:
                print(f"\n  {step.replace('_', ' ').title()}:")
                for cat in cats:
                    print(f"    - {cat}")

        # Filter lists
        print("\n📝 FILTER LISTS:")
        filters = diagnostic['filter_lists']

        print("\n  Allowed Categories:")
        if filters['allowed_custom']:
            for cat in filters['allowed_custom']:
                print(f"    ✓ {cat}")
        else:
            print("    (No allowed list - all categories allowed)")

        print("\n  Excluded Categories:")
        for cat in filters['excluded_custom']:
            print(f"    ✗ {cat}")

        # Final selection
        print("\n🎯 FINAL CUSTOM CATEGORY SELECTION:")
        final = diagnostic['final_selection']
        if final:
            for cat in final:
                print(f"\n  #{cat['rank']}: {cat['category']}")
                print(f"     Composite Index: {cat['composite_index']:.1f}")
                print(f"     Audience %: {cat['perc_audience']*100:.1f}%")
                print(f"     Index vs Gen Pop: {cat['perc_index']:.0f}")
                print(f"     Slide Title: '{cat['would_be_slide_title']}'")
        else:
            print("  ⚠️  NO CATEGORIES SELECTED!")

        print("\n" + "="*80)


def run_diagnostic(snowflake_connection, team_name: str, team_short: str,
                   league: str = "NBA", is_womens_team: bool = False):
    """
    Run the diagnostic on actual data

    Args:
        snowflake_connection: Active Snowflake connection
        team_name: Full team name (e.g., "Utah Jazz")
        team_short: Short team name (e.g., "Jazz")
        league: League name (default "NBA")
        is_womens_team: Whether this is a women's team
    """
    # Create diagnostic tool
    diagnostic = CategoryDiagnostic()

    # Build view name
    view_prefix = team_name.upper().replace(' ', '_')
    view_name = f"V_{view_prefix}_SIL_CATEGORY_INDEXING_ALL_TIME"

    print(f"\n🔄 Loading data from: {view_name}")

    # Query the data
    query = f"""
    SELECT 
        AUDIENCE,
        CATEGORY,
        COMPARISON_POPULATION,
        PERC_AUDIENCE,
        PERC_INDEX,
        COMPOSITE_INDEX,
        PPC,
        COMPARISON_PPC,
        SPC,
        AUDIENCE_COUNT,
        AUDIENCE_TOTAL_SPEND
    FROM SIL__TB_OTT_TEST.SC_TWINBRAINAI.{view_name}
    WHERE AUDIENCE = '{team_name} Fans'
    """

    try:
        category_df = pd.read_sql(query, snowflake_connection)
        print(f"✅ Loaded {len(category_df)} rows")

        # Run diagnostic
        diagnostic_report = diagnostic.analyze_category_selection(
            category_df, team_name, team_short, is_womens_team
        )

        # Print report
        diagnostic.print_diagnostic_report(diagnostic_report)

        # Also save to file
        import json
        output_file = f"category_diagnostic_{team_name.replace(' ', '_').lower()}.json"
        with open(output_file, 'w') as f:
            json.dump(diagnostic_report, f, indent=2, default=str)
        print(f"\n💾 Full diagnostic saved to: {output_file}")

    except Exception as e:
        print(f"\n❌ Error running diagnostic: {e}")
        raise


# Example usage
if __name__ == "__main__":
    # You would call this with your Snowflake connection
    # run_diagnostic(conn, "Utah Jazz", "Jazz", "NBA", False)

    # For testing without Snowflake, you can create sample data:
    print("\n📊 DIAGNOSTIC TOOL READY")
    print("Call run_diagnostic() with your Snowflake connection to analyze category selection")
    print("\nExample:")
    print("  run_diagnostic(conn, 'Utah Jazz', 'Jazz', 'NBA', False)")
    print("  run_diagnostic(conn, 'Dallas Cowboys', 'Cowboys', 'NFL', False)")