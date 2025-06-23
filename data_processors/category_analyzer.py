# data_processors/category_analyzer.py
"""
Process category and subcategory spending data for PowerPoint generation
Includes validation and data quality checks based on Snowflake data analysis
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
import yaml
import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CategoryMetrics:
    """Container for category-level metrics"""
    percent_fans: float
    percent_likely: float
    percent_purchases: float
    composite_index: float
    total_spend: float
    spc: float
    audience_count: int = 0
    comparison_population: str = ""

    def format_percent_fans(self) -> str:
        return f"{self.percent_fans * 100:.1f}%"

    def format_likelihood(self) -> str:
        return f"{abs(self.percent_likely):.0f}% {'More' if self.percent_likely > 0 else 'Less'}"

    def format_purchases(self) -> str:
        return f"{abs(self.percent_purchases):.0f}% {'more' if self.percent_purchases > 0 else 'fewer'}"

    def validate(self) -> List[str]:
        """Validate metrics for reasonable values"""
        issues = []

        if self.percent_fans > 1.0:
            issues.append(f"percent_fans > 100%: {self.percent_fans}")

        if abs(self.percent_likely) > 1000:
            issues.append(f"percent_likely unrealistic: {self.percent_likely}%")

        if self.spc < 0:
            issues.append(f"negative SPC: ${self.spc}")

        return issues


class CategoryAnalyzer:
    """Process category spending data for sports team analysis"""

    def __init__(self,
                 team_name: str = "Utah Jazz",
                 team_short: str = "Jazz",
                 league: str = "NBA",
                 config_path: Optional[Path] = None):
        """
        Initialize with team information and category configuration

        Args:
            team_name: Full team name (e.g., "Utah Jazz")
            team_short: Short team name (e.g., "Jazz")
            league: League name (e.g., "NBA")
            config_path: Path to categories.yaml
        """
        self.team_name = team_name
        self.team_short = team_short
        self.league = league

        # Set up audience names based on team
        self.audience_name = f"{team_name} Fans"
        self.comparison_pop = f"Local Gen Pop (Excl. {team_short})"
        self.league_fans = f"{league} Fans"

        # Load configuration
        if config_path is None:
            # Go up one level from data_processors to project root, then to config
            config_path = Path(__file__).parent.parent / 'config' / 'categories.yaml'

        if not config_path.exists():
            # Try alternative path if running from different location
            config_path = Path.cwd() / 'config' / 'categories.yaml'

        if not config_path.exists():
            raise FileNotFoundError(f"Could not find categories.yaml. Looked in:\n"
                                    f"  - {Path(__file__).parent.parent / 'config' / 'categories.yaml'}\n"
                                    f"  - {Path.cwd() / 'config' / 'categories.yaml'}")

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.categories = self.config['categories']
        self.excluded_custom = self.config['excluded_from_custom']

        # Validation thresholds
        self.max_reasonable_index = 1000  # 1000% = 10x more likely
        self.min_significant_difference = 5  # 5% minimum to report

    def analyze_category(self,
                         category_key: str,
                         category_df: pd.DataFrame,
                         subcategory_df: pd.DataFrame,
                         merchant_df: pd.DataFrame,
                         yoy_category_df: Optional[pd.DataFrame] = None,
                         yoy_merchant_df: Optional[pd.DataFrame] = None,
                         validate: bool = True) -> Dict[str, Any]:
        """
        Analyze a specific category using multiple data sources

        Args:
            category_key: Category identifier from config
            category_df: Data from CATEGORY_INDEXING_ALL_TIME view
            subcategory_df: Data from SUBCATEGORY_INDEXING_ALL_TIME view
            merchant_df: Data from MERCHANT_INDEXING_ALL_TIME view
            yoy_category_df: Optional YOY category data
            yoy_merchant_df: Optional YOY merchant data
            validate: Whether to run validation checks

        Returns:
            Complete analysis results including metrics, insights, and recommendations
        """
        # Get category configuration
        category_config = self.categories.get(category_key)
        if not category_config:
            raise ValueError(f"Unknown category: {category_key}")

        # Clean data - TRIM all string columns and remove nulls
        for df in [category_df, subcategory_df, merchant_df]:
            if df is not None and not df.empty:
                self._clean_dataframe(df)

        # Store raw data for validation
        self.raw_data = {
            'category': category_df,
            'subcategory': subcategory_df,
            'merchant': merchant_df
        }

        # 1. Category-level analysis
        category_metrics = self._get_category_metrics(category_df, category_config)

        # Validate metrics if requested
        if validate:
            metric_issues = category_metrics.validate()
            if metric_issues:
                logger.warning(f"Metric validation issues: {metric_issues}")

        # 2. Subcategory analysis
        subcategory_stats = self._get_subcategory_stats(subcategory_df, category_config)

        # 3. Generate insights with proper data sources
        insights = self._generate_insights(
            category_config, category_metrics, subcategory_stats,
            category_df, subcategory_df, yoy_category_df
        )

        # 4. Merchant analysis
        merchant_stats = self._get_merchant_stats(merchant_df)

        # 5. Generate merchant insights
        merchant_insights = self._generate_merchant_insights(
            merchant_stats, merchant_df, yoy_merchant_df
        )

        # 6. Get sponsorship recommendation
        recommendation = self._get_sponsorship_recommendation(merchant_df)

        # 7. Run validation if requested
        validation_report = None
        if validate:
            validation_report = self._validate_results(
                category_metrics, insights, merchant_insights
            )

        return {
            'category_key': category_key,
            'display_name': category_config['display_name'],
            'slide_title': category_config['slide_title'],
            'category_metrics': category_metrics,
            'subcategory_stats': subcategory_stats,
            'insights': insights,
            'merchant_stats': merchant_stats,
            'merchant_insights': merchant_insights,
            'recommendation': recommendation,
            'validation_report': validation_report
        }

    def _clean_dataframe(self, df: pd.DataFrame):
        """Clean dataframe in place"""
        # Strip whitespace from string columns
        string_cols = df.select_dtypes(include=['object']).columns
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()

        # Remove rows with null audiences
        if 'AUDIENCE' in df.columns:
            df.dropna(subset=['AUDIENCE'], inplace=True)

    def _get_category_metrics(self, df: pd.DataFrame,
                              category_config: Dict[str, Any]) -> CategoryMetrics:
        """Extract category-level metrics"""
        if df.empty:
            logger.warning(f"No category data found")
            return CategoryMetrics(0, 0, 0, 0, 0, 0, 0, self.comparison_pop)

        # Filter for team fans vs comparison population
        comp_data = df[
            (df['AUDIENCE'] == self.audience_name) &
            (df['COMPARISON_POPULATION'] == self.comparison_pop)
            ]

        if comp_data.empty:
            logger.warning(f"No comparison data found for {self.comparison_pop}")
            return CategoryMetrics(0, 0, 0, 0, 0, 0, 0, self.comparison_pop)

        # Get metrics from the row
        row = comp_data.iloc[0]
        percent_fans = float(row['PERC_AUDIENCE'])
        percent_likely = float(row['PERC_INDEX']) - 100

        # Calculate purchase difference
        ppc = float(row['PPC'])
        comp_ppc = float(row['COMPARISON_PPC'])
        percent_purchases = self._calculate_percent_diff(ppc, comp_ppc)

        return CategoryMetrics(
            percent_fans=percent_fans,
            percent_likely=percent_likely,
            percent_purchases=percent_purchases,
            composite_index=float(row.get('COMPOSITE_INDEX', 0)),
            total_spend=float(row.get('AUDIENCE_TOTAL_SPEND', 0)),
            spc=float(row.get('SPC', 0)),
            audience_count=int(row.get('AUDIENCE_COUNT', 0)),
            comparison_population=self.comparison_pop
        )

    def _get_subcategory_stats(self, df: pd.DataFrame,
                               category_config: Dict[str, Any]) -> pd.DataFrame:
        """Get subcategory statistics formatted for display"""
        if df.empty:
            return pd.DataFrame()

        # Filter for team fans vs comparison population specifically
        team_data = df[
            (df['AUDIENCE'] == self.audience_name) &
            (df['COMPARISON_POPULATION'] == self.comparison_pop)
            ].copy()

        if team_data.empty:
            return pd.DataFrame()

        # Check if this is a custom category
        is_custom = category_config.get('is_custom', False)

        if is_custom:
            # For custom categories, include ALL subcategories from the data
            # Don't apply any include/exclude filters
            logger.info(
                f"Processing custom category {category_config.get('display_name')} - using all subcategories from data")

            # Remove any rows with empty/null subcategories
            team_data = team_data[team_data['SUBCATEGORY'].notna() & (team_data['SUBCATEGORY'] != '')]

        else:
            # For fixed categories, apply the YAML configuration filters
            subcats = category_config.get('subcategories', {})

            if 'include' in subcats and isinstance(subcats['include'], list):
                # Get the keys to include
                include_keys = []
                for sc in subcats['include']:
                    key = sc['key_in_data']
                    if isinstance(key, list):
                        include_keys.extend(key)
                    else:
                        include_keys.append(key)

                team_data = team_data[team_data['SUBCATEGORY'].isin(include_keys)]

            if 'exclude' in subcats:
                team_data = team_data[~team_data['SUBCATEGORY'].isin(subcats['exclude'])]

        # Get top 5 by audience percentage - ensure no duplicates
        top_5 = (team_data
                 .drop_duplicates('SUBCATEGORY')
                 .sort_values('PERC_AUDIENCE', ascending=False)
                 .head(5))

        # Build display table
        results = []
        for _, row in top_5.iterrows():
            subcategory = row['SUBCATEGORY']

            # Since we already filtered for the correct comparison population,
            # we can use the row data directly
            percent_likely = float(row['PERC_INDEX']) - 100
            percent_purch = self._calculate_percent_diff(
                float(row['PPC']),
                float(row['COMPARISON_PPC'])
            )

            # Format subcategory name for display
            display_name = self._format_subcategory_name(subcategory, category_config)

            results.append({
                'Subcategory': display_name,
                'Percent of Fans Who Spend': f"{row['PERC_AUDIENCE'] * 100:.1f}%",
                'How likely fans are to spend vs. gen pop':
                    f"{abs(percent_likely):.0f}% {'More' if percent_likely > 0 else 'Less'}",
                'Purchases per fan vs. gen pop':
                    f"{abs(percent_purch):.0f}% {'more' if percent_purch > 0 else 'Less'}"
            })

        return pd.DataFrame(results)

    def _get_merchant_stats(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Get top merchant statistics"""
        if df.empty:
            return pd.DataFrame(), []

        # Filter for team fans
        team_data = df[df['AUDIENCE'] == self.audience_name]

        if team_data.empty:
            return pd.DataFrame(), []

        # Get top 5 merchants by audience percentage
        top_5_merchants = (team_data
                           .sort_values('PERC_AUDIENCE', ascending=False)
                           .drop_duplicates('MERCHANT')
                           .head(5)['MERCHANT'].tolist())

        # Build comparison table
        results = []
        for merchant in top_5_merchants:
            comp_data = df[
                (df['AUDIENCE'] == self.audience_name) &
                (df['MERCHANT'] == merchant) &
                (df['COMPARISON_POPULATION'] == self.comparison_pop)
                ]

            if not comp_data.empty:
                row = comp_data.iloc[0]
                percent_fans = float(row['PERC_AUDIENCE']) * 100
                percent_likely = float(row['PERC_INDEX']) - 100
                ppc_diff = self._calculate_percent_diff(
                    float(row['PPC']),
                    float(row['COMPARISON_PPC'])
                )

                results.append({
                    'Brand': merchant,
                    'Percent of Fans Who Spend': f"{percent_fans:.1f}%",
                    'How likely fans are to spend vs. gen pop':
                        f"{abs(percent_likely):.0f}% {'More' if percent_likely >= 0 else 'Less'}",
                    'Purchases Per Fan (vs. Gen Pop)':
                        f"{abs(ppc_diff):.0f}% {'More' if ppc_diff >= 0 else 'Less'}"
                })

        if results:
            merchant_df = pd.DataFrame(results)
            merchant_df['Rank'] = range(1, len(merchant_df) + 1)

            # Reorder columns
            cols = ['Rank', 'Brand', 'Percent of Fans Who Spend',
                    'How likely fans are to spend vs. gen pop',
                    'Purchases Per Fan (vs. Gen Pop)']

            return merchant_df[cols], top_5_merchants

        return pd.DataFrame(), top_5_merchants

    def _generate_insights(self, category_config: Dict[str, Any],
                           metrics: CategoryMetrics,
                           subcategory_stats: pd.DataFrame,
                           category_df: pd.DataFrame,
                           subcategory_df: pd.DataFrame,
                           yoy_df: Optional[pd.DataFrame]) -> List[str]:
        """Generate category insights following template patterns"""
        insights = []

        # 1. Likelihood to spend
        if abs(metrics.percent_likely) >= self.min_significant_difference:
            insights.append(
                f"{self.team_short} Fans are {abs(metrics.percent_likely):.0f}% "
                f"{'MORE' if metrics.percent_likely > 0 else 'LESS'} likely to spend on "
                f"{category_config['display_name']} than the {self.comparison_pop}"
            )

        # 2. Purchase frequency
        if abs(metrics.percent_purchases) >= self.min_significant_difference:
            insights.append(
                f"{self.team_short} Fans make an average of {abs(metrics.percent_purchases):.0f}% "
                f"{'more' if metrics.percent_purchases > 0 else 'fewer'} purchases per fan on "
                f"{category_config['display_name']} than the {self.comparison_pop}"
            )

        # 3. Top subcategory highlight (only if we have subcategory data)
        if not subcategory_stats.empty:
            top_sub = subcategory_stats.iloc[0]
            self._add_subcategory_insight(insights, top_sub)

        # 4. Spending amount insight (QSR specific for restaurants)
        if category_config['display_name'] == 'Restaurants':
            self._add_qsr_insight(insights, subcategory_df)

        # 5. Year-over-year insight
        if yoy_df is not None and not yoy_df.empty:
            yoy_insight = self._get_yoy_insight(yoy_df, category_config['display_name'])
            if yoy_insight:
                insights.append(yoy_insight)

        # 6. NBA/League comparison - use category data, NOT merchant data
        nba_insight = self._get_league_comparison_category(category_df, category_config['display_name'])
        if nba_insight:
            insights.append(nba_insight)

        return insights

    def _add_subcategory_insight(self, insights: List[str], top_sub: pd.Series):
        """Add subcategory insight with validation"""
        likelihood_text = top_sub['How likely fans are to spend vs. gen pop']

        if '% More' in likelihood_text:
            try:
                percent = float(likelihood_text.split('%')[0])

                # Validate reasonable range
                if percent > self.max_reasonable_index:
                    logger.warning(f"Subcategory index too high: {percent}%, skipping insight")
                    return

                if percent > 200:
                    multiplier = round(percent / 100, 1)
                    insights.append(
                        f"{self.team_short} Fans are more than {multiplier}X more likely "
                        f"to spend on {top_sub['Subcategory']} vs. the {self.comparison_pop}"
                    )
                else:
                    insights.append(
                        f"{self.team_short} Fans are {likelihood_text} likely to spend on "
                        f"{top_sub['Subcategory']} vs. the {self.comparison_pop}"
                    )
            except ValueError:
                logger.error(f"Could not parse likelihood: {likelihood_text}")

    def _add_qsr_insight(self, insights: List[str], subcategory_df: pd.DataFrame):
        """Add QSR insight using correct subcategory data"""
        if subcategory_df.empty:
            return

        # Find QSR data for team fans vs local gen pop
        qsr_data = subcategory_df[
            (subcategory_df['AUDIENCE'] == self.audience_name) &
            (subcategory_df['SUBCATEGORY'].str.contains('QSR', case=False, na=False)) &
            (subcategory_df['COMPARISON_POPULATION'] == self.comparison_pop)
            ]

        if not qsr_data.empty:
            qsr_spc = float(qsr_data.iloc[0]['SPC'])
            insights.append(
                f"{self.team_short} fans spend an average of ${qsr_spc:.2f} per fan per year "
                f"on QSR and Fast Casual Restaurants"
            )

    def _generate_merchant_insights(self, merchant_stats: Tuple[pd.DataFrame, List[str]],
                                    merchant_df: pd.DataFrame,
                                    yoy_merchant_df: Optional[pd.DataFrame]) -> List[str]:
        """Generate merchant-specific insights"""
        merchant_table, top_merchants = merchant_stats
        insights = []

        if merchant_table.empty or not top_merchants:
            return insights

        # 1. Top merchant spending
        top_merchant = merchant_table.iloc[0]
        insights.append(
            f"{top_merchant['Percent of Fans Who Spend']} of {self.team_name} fans "
            f"spent at {top_merchant['Brand']}"
        )

        # 2. Purchase frequency insight with actual data
        if yoy_merchant_df is not None and not yoy_merchant_df.empty:
            # Get average purchases for top merchants
            yoy_merchant_df = yoy_merchant_df[
                yoy_merchant_df['MERCHANT'].isin(top_merchants)
            ]

            if not yoy_merchant_df.empty:
                # Average PPC across years for each merchant
                ppc_avg = yoy_merchant_df.groupby('MERCHANT')['PPC'].mean()
                if not ppc_avg.empty:
                    top_ppc_merchant = ppc_avg.idxmax()
                    avg_purchases = ppc_avg.max()
                    insights.append(
                        f"{self.team_name} fans average {avg_purchases:.0f} purchases "
                        f"per year per fan at {top_ppc_merchant}"
                    )

                # Get SPC data for third merchant
                spc_avg = yoy_merchant_df.groupby('MERCHANT')['SPC'].mean()
                if len(top_merchants) > 2 and not spc_avg.empty:
                    third_merchant = top_merchants[2]
                    if third_merchant in spc_avg:
                        avg_spend = spc_avg[third_merchant]
                        insights.append(
                            f"{self.team_name} fans spent an average of ${avg_spend:.2f} per fan on "
                            f"{third_merchant} per year"
                        )

        # 4. Merchant NBA comparison (if available)
        if len(top_merchants) > 3:
            fourth_merchant = top_merchants[3]
            nba_merchant_insight = self._get_merchant_nba_comparison(merchant_df, fourth_merchant)
            if nba_merchant_insight:
                insights.append(nba_merchant_insight)
            else:
                insights.append(
                    f"{self.team_name} fans show strong affinity for {fourth_merchant}"
                )

        return insights

    def _get_merchant_nba_comparison(self, merchant_df: pd.DataFrame, merchant: str) -> Optional[str]:
        """Get NBA comparison for specific merchant"""
        nba_data = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['MERCHANT'] == merchant) &
            (merchant_df['COMPARISON_POPULATION'] == self.league_fans)
            ]

        if not nba_data.empty:
            perc_index = float(nba_data.iloc[0]['PERC_INDEX'])
            index_diff = perc_index - 100

            if abs(index_diff) >= self.min_significant_difference:
                return (
                    f"{self.team_name} fans are {abs(index_diff):.0f}% "
                    f"{'more' if index_diff > 0 else 'less'} likely to spend on {merchant} "
                    f"than {self.league} Fans."
                )

        return None

    def _get_league_comparison_category(self, category_df: pd.DataFrame, category_name: str) -> Optional[str]:
        """Get comparison to league average at category level (NOT merchant level)"""
        if category_df.empty:
            return None

        # Look for league comparison data in CATEGORY data
        league_comp = category_df[
            (category_df['AUDIENCE'] == self.audience_name) &
            (category_df['COMPARISON_POPULATION'] == self.league_fans)
            ]

        if league_comp.empty:
            return None

        # Get the index difference
        perc_index = float(league_comp.iloc[0]['PERC_INDEX'])
        index_diff = perc_index - 100

        # Only report if significant difference (>5%)
        if abs(index_diff) > self.min_significant_difference:
            if index_diff > 0:
                return (
                    f"{self.team_name} fans are {index_diff:.0f}% more likely "
                    f"to spend on {category_name} when compared to the {self.league} average"
                )
            else:
                return (
                    f"{self.team_name} fans are {abs(index_diff):.0f}% less likely "
                    f"to spend on {category_name} when compared to the {self.league} average"
                )

        return None

    def _get_sponsorship_recommendation(self, merchant_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Get top sponsorship recommendation based on composite index"""
        if merchant_df.empty:
            return None

        # Get merchant with highest composite index
        team_comp_data = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['COMPARISON_POPULATION'] == self.comparison_pop)
            ]

        if team_comp_data.empty:
            return None

        top_composite = team_comp_data.nlargest(1, 'COMPOSITE_INDEX').iloc[0]

        return {
            'merchant': top_composite['MERCHANT'],
            'composite_index': float(top_composite['COMPOSITE_INDEX']),
            'explanation': (
                f"Fans are more likely to spend with {top_composite['MERCHANT']} "
                f"and more likely to spend MORE per consumer vs. the {self.comparison_pop} "
                f"on {top_composite['MERCHANT']}"
            )
        }

    def _validate_results(self, metrics: CategoryMetrics,
                          insights: List[str],
                          merchant_insights: List[str]) -> Dict[str, Any]:
        """Validate results against raw data"""
        issues = []

        # Check insights for known issues
        for insight in insights:
            # Check for the 991% issue (should not appear in category insights)
            if "991%" in insight or any(str(x) + "%" in insight for x in range(900, 1100)):
                issues.append(f"Suspiciously high percentage in insight: {insight}")

            # Check for $3311 QSR issue
            if "$3311" in insight and "QSR" in insight:
                issues.append("Using category SPC for QSR subcategory")

            # Check for unrealistic NBA comparisons
            if "NBA" in insight and any(str(x) + "%" in insight for x in range(500, 20000)):
                issues.append(f"Unrealistic NBA comparison: {insight}")

        # Validate metrics
        metric_issues = metrics.validate()
        if metric_issues:
            issues.extend(metric_issues)

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'timestamp': datetime.now().isoformat()
        }

    # Helper methods
    def _calculate_percent_diff(self, value1: float, value2: float) -> float:
        """Calculate percentage difference"""
        if value2 == 0:
            return 0
        return ((value1 - value2) / value2) * 100

    def _format_subcategory_name(self, subcategory: str, category_config: Dict[str, Any]) -> str:
        """Format subcategory name for display"""
        # For custom categories, just clean up the name
        if category_config.get('is_custom', False):
            # Remove category prefix if it exists
            category_name = category_config.get('display_name', '')
            if subcategory.startswith(f"{category_name} - "):
                return subcategory.replace(f"{category_name} - ", "")
            return subcategory

        # For fixed categories, use the existing logic
        for cat_name in category_config.get('category_names_in_data', []):
            if subcategory.startswith(f"{cat_name} - "):
                return subcategory.replace(f"{cat_name} - ", "")
        return subcategory

    def _get_yoy_insight(self, yoy_df: pd.DataFrame, category_name: str) -> Optional[str]:
        """Generate year-over-year insight"""
        # Filter for recent years
        yoy_df = yoy_df[yoy_df['TRANSACTION_YEAR'].isin(['2023-01-01', '2024-01-01'])]

        if len(yoy_df) < 2:
            return None

        yoy_df = yoy_df.sort_values('TRANSACTION_YEAR')
        pct_2023 = float(yoy_df.iloc[0]['PERC_AUDIENCE'])
        pct_2024 = float(yoy_df.iloc[1]['PERC_AUDIENCE'])

        pct_change = ((pct_2024 - pct_2023) / pct_2023) * 100

        if pct_change > 5:  # Only mention if significant
            return (
                f"{category_name} saw an increase of {pct_change:.0f}% of {self.team_short} "
                f"fans spending on the category in 2024 vs. 2023"
            )

        return None

    def get_custom_categories(self,
                              category_df: pd.DataFrame,
                              is_womens_team: bool = False,
                              existing_categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get custom categories based on composite index

        Args:
            category_df: DataFrame from CATEGORY_INDEXING_ALL_TIME view
            is_womens_team: Whether this is a women's team
            existing_categories: List of category keys already included (fixed categories)

        Returns:
            List of category configurations for custom categories
        """
        # Get config
        custom_config = self.config.get('custom_category_config', {})
        n_categories = (custom_config.get('womens_teams', {}).get('count', 2) if is_womens_team
                        else custom_config.get('mens_teams', {}).get('count', 4))
        min_audience = custom_config.get('min_audience_pct', 0.20)

        # Default existing categories if not provided
        if existing_categories is None:
            existing_categories = ['restaurants', 'athleisure', 'finance', 'gambling', 'travel', 'auto']
            if is_womens_team:
                existing_categories.extend(['beauty', 'health'])

        # Get the actual category names from config for existing categories
        existing_category_names = set()
        for cat_key in existing_categories:
            if cat_key in self.categories:
                cat_names = self.categories[cat_key].get('category_names_in_data', [])
                existing_category_names.update(cat_names)

        # Filter to only team fans vs local gen pop with sufficient audience
        team_data = category_df[
            (category_df['AUDIENCE'] == self.audience_name) &
            (category_df['COMPARISON_POPULATION'] == self.comparison_pop) &
            (category_df['PERC_AUDIENCE'] >= min_audience)
            ].copy()

        if team_data.empty:
            logger.warning("No category data found for custom category selection")
            return []

        # Remove duplicates (keep highest composite index per category)
        team_data = team_data.sort_values('COMPOSITE_INDEX', ascending=False).drop_duplicates('CATEGORY')

        # Filter out existing categories and excluded categories
        available_data = team_data[
            ~team_data['CATEGORY'].isin(existing_category_names) &
            ~team_data['CATEGORY'].isin(self.excluded_custom)
            ]

        # Also filter out any women's only categories if this is a men's team
        if not is_womens_team:
            # Remove Beauty and Health categories
            available_data = available_data[
                ~available_data['CATEGORY'].isin(['Beauty', 'Health'])
            ]

        # Sort by composite index and take top N
        top_categories = available_data.nlargest(n_categories, 'COMPOSITE_INDEX')

        # Convert to list of category info
        custom_categories = []
        for _, row in top_categories.iterrows():
            category_name = row['CATEGORY']

            # Create a dynamic category config
            category_info = {
                'category_key': category_name.lower().replace(' ', '_').replace('-', '_'),
                'display_name': category_name,
                'category_names_in_data': [category_name],
                'composite_index': float(row['COMPOSITE_INDEX']),
                'audience_pct': float(row['PERC_AUDIENCE']),
                'perc_index': float(row['PERC_INDEX']),
                'is_custom': True
            }

            custom_categories.append(category_info)

        logger.info(f"Selected {len(custom_categories)} custom categories")
        for cat in custom_categories:
            logger.info(f"  - {cat['display_name']} (composite index: {cat['composite_index']:.1f})")

        return custom_categories

    def create_custom_category_config(self, category_name: str) -> Dict[str, Any]:
        """
        Create a category configuration for a custom category

        Args:
            category_name: Name of the category from the data

        Returns:
            Category configuration similar to what's in categories.yaml
        """
        # Generate a reasonable slide title
        slide_title = f"{category_name} Sponsor Analysis"

        # Create the config
        config = {
            'display_name': category_name,
            'slide_title': slide_title,
            'category_names_in_data': [category_name],
            'subcategories': {
                # Empty for custom categories - we'll use all subcategories from data
                'include': [],
                'exclude': []
            },
            'is_custom': True  # This flag is crucial!
        }

        return config