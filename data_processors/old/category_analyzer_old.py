# data_processors/category_analyzer.py
"""
Category analyzer that processes spending data by category
Generates insights and recommendations for sponsorship opportunities
ENHANCED with OpenAI-powered merchant name standardization
UPDATED to use allowed_for_custom list for custom category selection
UPDATED with consistent column names for slide compatibility
UPDATED to use LAST_FULL_YEAR views for specific insights
UPDATED with subcategory name override support
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import yaml
import logging
import asyncio
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CategoryMetrics:
    """Data class for category-level metrics"""
    percent_fans: float  # Percentage of fans who spend in category
    percent_likely: float  # How much more/less likely to spend
    percent_purchases: float  # Purchase frequency difference
    composite_index: float  # Combined metric
    total_spend: float  # Total category spend
    spc: float  # Spend per customer
    audience_count: int  # Number of fans
    comparison_population: str  # Who we're comparing to

    def format_percent_fans(self) -> str:
        """Format percentage of fans who spend"""
        return f"{self.percent_fans * 100:.0f}%"

    def format_likelihood(self) -> str:
        """Format likelihood comparison"""
        if abs(self.percent_likely) < 1:
            return "Equally likely"
        return f"{abs(self.percent_likely):.0f}% {'More' if self.percent_likely > 0 else 'Less'} likely"

    def format_purchases(self) -> str:
        """Format purchase frequency comparison"""
        if abs(self.percent_purchases) < 1:
            return "Equal purchases"
        return f"{abs(self.percent_purchases):.0f}% {'More' if self.percent_purchases > 0 else 'Fewer'}"

    def validate(self) -> List[str]:
        """Validate metrics are reasonable"""
        issues = []
        if self.percent_fans > 1.0:
            issues.append(f"Percent fans > 100%: {self.percent_fans * 100:.1f}%")
        if abs(self.percent_likely) > 1000:
            issues.append(f"Likelihood unrealistic: {self.percent_likely:.0f}%")
        if self.composite_index > 2000:
            issues.append(f"Composite index too high: {self.composite_index:.1f}")
        return issues


class CategoryAnalyzer:
    """Analyzes category spending data and generates insights with merchant name standardization"""

    def __init__(self, team_name: str, team_short: str, league: str,
                 config_path: Optional[Path] = None,
                 comparison_population: str = None):
        """
        Initialize the category analyzer with merchant name standardization

        Args:
            team_name: Full team name (e.g., "Utah Jazz")
            team_short: Short team name (e.g., "Jazz")
            league: League name (e.g., "NBA")
            config_path: Path to categories config file
        """
        self.team_name = team_name
        self.team_short = team_short
        self.league = league

        # Standard audiences
        self.audience_name = f"{team_name} Fans"
        # Use provided comparison_population or fallback to old logic
        if comparison_population:
            self.comparison_pop = comparison_population  # USE EXACT VALUE FROM CONFIG
        else:
            # Fallback to old logic
            self.comparison_pop = f"Local Gen Pop (Excl. {team_short})"
        self.league_fans = f"{league} Fans"

        # Initialize merchant name standardizer
        try:
            from utils.merchant_name_standardizer import MerchantNameStandardizer
            self.standardizer = MerchantNameStandardizer(cache_enabled=True)
            logger.info("✅ CategoryAnalyzer: Merchant name standardization enabled")
        except ImportError:
            logger.warning("⚠️ CategoryAnalyzer: MerchantNameStandardizer not available")
            self.standardizer = None

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
        self.allowed_custom = self.config.get('allowed_for_custom', [])  # NEW: Get allowed list

        # NEW: Load subcategory name overrides
        self.subcategory_overrides = self.config.get('subcategory_name_overrides', {})

        # Validation thresholds
        self.max_reasonable_index = 1000  # 1000% = 10x more likely
        self.min_significant_difference = 0  # No minimum threshold - report all differences

    def standardize_merchant_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize merchant names in merchant DataFrame

        Args:
            df: DataFrame with 'MERCHANT' column

        Returns:
            DataFrame with standardized merchant names
        """
        if 'MERCHANT' not in df.columns or df.empty or self.standardizer is None:
            return df

        try:
            logger.info(
                f"🔄 CategoryAnalyzer: Standardizing merchant names for {len(df['MERCHANT'].unique())} unique merchants...")

            # Get unique names
            unique_names = df['MERCHANT'].dropna().unique().tolist()

            if not unique_names:
                return df

            # Preserve original names
            df['MERCHANT_ORIGINAL'] = df['MERCHANT'].copy()

            # Get standardized mapping
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                name_mapping = loop.run_until_complete(self.standardizer.standardize_merchants(unique_names))
            finally:
                loop.close()

            # OVERWRITE THE MERCHANT COLUMN
            df['MERCHANT'] = df['MERCHANT'].map(name_mapping).fillna(df['MERCHANT'])

            logger.info("✅ CategoryAnalyzer: Merchant name standardization completed")
            return df

        except Exception as e:
            logger.warning(f"⚠️ CategoryAnalyzer: Merchant name standardization failed: {e}")
            return df

    def analyze_category(self,
                         category_key: str,
                         category_df: pd.DataFrame,
                         subcategory_df: pd.DataFrame,
                         merchant_df: pd.DataFrame,
                         # NEW: Add optional DataFrames for LAST_FULL_YEAR
                         subcategory_last_year_df: pd.DataFrame = None,
                         merchant_last_year_df: pd.DataFrame = None,
                         validate: bool = True) -> Dict[str, Any]:
        """
        Analyze a specific category using multiple data sources with merchant name standardization

        Args:
            category_key: Category identifier from config
            category_df: Data from CATEGORY_INDEXING_ALL_TIME view
            subcategory_df: Data from SUBCATEGORY_INDEXING_ALL_TIME view
            merchant_df: Data from MERCHANT_INDEXING_ALL_TIME view
            subcategory_last_year_df: Data from SUBCATEGORY_INDEXING_LAST_FULL_YEAR view (NEW)
            merchant_last_year_df: Data from MERCHANT_INDEXING_LAST_FULL_YEAR view (NEW)
            validate: Whether to run validation checks

        Returns:
            Complete analysis results including metrics, insights, and recommendations
        """
        # Get category configuration
        category_config = self.categories.get(category_key)
        if not category_config:
            raise ValueError(f"Unknown category: {category_key}")

        # Clean data - TRIM all string columns and remove nulls
        for df in [category_df, subcategory_df, merchant_df, subcategory_last_year_df, merchant_last_year_df]:
            if df is not None and not df.empty:
                self._clean_dataframe(df)

        # STANDARDIZE MERCHANT NAMES FIRST
        if not merchant_df.empty and 'MERCHANT' in merchant_df.columns:
            merchant_df = self.standardize_merchant_data(merchant_df)

        # Standardize LAST_FULL_YEAR merchant data if provided
        if merchant_last_year_df is not None and not merchant_last_year_df.empty and 'MERCHANT' in merchant_last_year_df.columns:
            merchant_last_year_df = self.standardize_merchant_data(merchant_last_year_df)

        # Store raw data for validation (AFTER standardization)
        self.raw_data = {
            'category': category_df,
            'subcategory': subcategory_df,
            'merchant': merchant_df,
            'subcategory_last_year': subcategory_last_year_df,  # NEW
            'merchant_last_year': merchant_last_year_df  # NEW
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
        # Pass LAST_FULL_YEAR data for specific insights
        insights = self._generate_insights(
            category_config, category_metrics, subcategory_stats,
            category_df, subcategory_df,
            subcategory_last_year_df  # NEW: Pass LAST_FULL_YEAR data
        )

        # 4. Merchant analysis (now with standardized names)
        merchant_stats = self._get_merchant_stats(merchant_df)

        # 5. Generate merchant insights (now with standardized names)
        # Pass LAST_FULL_YEAR merchant data
        merchant_insights = self._generate_merchant_insights(
            merchant_stats, merchant_df,
            merchant_last_year_df  # NEW: Pass LAST_FULL_YEAR data
        )

        # 6. Get sponsorship recommendation (now with standardized names)
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
                df.loc[:, col] = df[col].astype(str).str.strip()

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

        # KEEP THE SUBTRACTION - This gives us "% MORE likely"
        percent_likely = float(row['PERC_INDEX']) - 100  # 430 - 100 = 330% MORE

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
            team_data = team_data[team_data['SUBCATEGORY'].notna()]
        else:
            # For fixed categories, apply include/exclude logic
            subcategory_config = category_config.get('subcategories', {})
            included = subcategory_config.get('include', [])
            excluded = subcategory_config.get('exclude', [])

            # Build subcategory filter
            if included:
                # Use specific included subcategories
                included_names = [sub['key_in_data'] if isinstance(sub, dict) else sub
                                  for sub in included]
                # Handle lists (like Auto Parts & Service)
                all_included = []
                for name in included_names:
                    if isinstance(name, list):
                        all_included.extend(name)
                    else:
                        all_included.append(name)
                team_data = team_data[team_data['SUBCATEGORY'].isin(all_included)]
            elif excluded:
                # Exclude specific subcategories
                team_data = team_data[~team_data['SUBCATEGORY'].isin(excluded)]

        if team_data.empty:
            return pd.DataFrame()

        # Sort by composite index and take top 4
        top_subcategories = team_data.nlargest(4, 'COMPOSITE_INDEX')

        # Format for display
        results = []
        for _, row in top_subcategories.iterrows():
            percent_fans = float(row['PERC_AUDIENCE']) * 100

            # KEEP THE SUBTRACTION - This gives us "% MORE likely"
            percent_likely = float(row['PERC_INDEX']) - 100  # 430 - 100 = 330% MORE

            percent_purch = self._calculate_percent_diff(
                float(row['PPC']),
                float(row['COMPARISON_PPC'])
            )

            # Format subcategory name
            subcategory_name = self._format_subcategory_name(
                row['SUBCATEGORY'], category_config
            )

            results.append({
                'Subcategory': subcategory_name,
                'Percent of Fans Who Spend': f"{percent_fans:.0f}%",
                'Likelihood to spend (vs. Local Gen Pop)':  # UPDATED to match slide header
                    f"{abs(percent_likely):.0f}% {'More' if percent_likely > 0 else 'Less'}",
                'Purchases Per Fan (vs. Gen Pop)':
                    f"{abs(percent_purch):.0f}% {'More' if percent_purch > 0 else 'Less'}"
            })

        return pd.DataFrame(results)

    def _get_merchant_stats(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Get top merchant statistics (now with standardized names)"""
        if df.empty:
            return pd.DataFrame(), []

        # Filter for team fans
        team_data = df[df['AUDIENCE'] == self.audience_name]

        if team_data.empty:
            return pd.DataFrame(), []

        # Get top 5 merchants by audience percentage (using standardized names)
        top_5_merchants = (team_data
                           .sort_values('PERC_AUDIENCE', ascending=False)
                           .drop_duplicates('MERCHANT')
                           .head(5)['MERCHANT'].tolist())

        # Build comparison table (now with standardized names)
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

                # KEEP THE SUBTRACTION - This gives us "% MORE likely"
                percent_likely = float(row['PERC_INDEX']) - 100  # 430 - 100 = 330% MORE

                ppc_diff = self._calculate_percent_diff(
                    float(row['PPC']),
                    float(row['COMPARISON_PPC'])
                )

                results.append({
                    'Brand': merchant,  # Now using standardized names
                    'Percent of Fans Who Spend': f"{percent_fans:.1f}%",
                    'Likelihood to spend (vs. Local Gen Pop)':  # UPDATED to match slide header
                        f"{abs(percent_likely):.0f}% {'More' if percent_likely >= 0 else 'Less'}",
                    'Purchases Per Fan (vs. Gen Pop)':
                        f"{abs(ppc_diff):.0f}% {'More' if ppc_diff >= 0 else 'Less'}"
                })

        if results:
            merchant_df = pd.DataFrame(results)
            merchant_df['Rank'] = range(1, len(merchant_df) + 1)

            # Reorder columns
            cols = ['Rank', 'Brand', 'Percent of Fans Who Spend',
                    'Likelihood to spend (vs. Local Gen Pop)',  # UPDATED
                    'Purchases Per Fan (vs. Gen Pop)']

            return merchant_df[cols], top_5_merchants

        return pd.DataFrame(), top_5_merchants

    def _generate_insights(self, category_config: Dict[str, Any],
                           metrics: CategoryMetrics,
                           subcategory_stats: pd.DataFrame,
                           category_df: pd.DataFrame,
                           subcategory_df: pd.DataFrame,
                           subcategory_last_year_df: pd.DataFrame = None) -> List[str]:
        """Generate category insights following template patterns"""
        insights = []

        # 1. Likelihood to spend
        insights.append(
            f"{self.team_short} fans are {abs(metrics.percent_likely):.0f}% "
            f"{'MORE' if metrics.percent_likely > 0 else 'LESS'} likely to spend on "
            f"{category_config['display_name']} than the {self.comparison_pop}"
        )

        # 2. Purchase frequency
        insights.append(
            f"{self.team_short} fans make an average of {abs(metrics.percent_purchases):.0f}% "
            f"{'more' if metrics.percent_purchases > 0 else 'fewer'} purchases per fan on "
            f"{category_config['display_name']} than the {self.comparison_pop}"
        )

        # 3. Top subcategory highlight (only if we have subcategory data)
        if not subcategory_stats.empty:
            top_sub = subcategory_stats.iloc[0]
            self._add_subcategory_insight(insights, top_sub)

        # 4. Highest spending subcategory - NOW USES LAST_FULL_YEAR if available
        if subcategory_last_year_df is not None and not subcategory_last_year_df.empty:
            self._add_highest_spend_subcategory_insight(insights, subcategory_last_year_df)
        else:
            # Fallback to ALL_TIME if LAST_FULL_YEAR not provided
            self._add_highest_spend_subcategory_insight(insights, subcategory_df)

        # 5. NBA/League comparison - use subcategory data
        nba_insight = self._get_league_comparison_subcategory(subcategory_df, category_config)
        if nba_insight:
            insights.append(nba_insight)

        return insights

    def _add_subcategory_insight(self, insights: List[str], top_sub: pd.Series):
        """Add subcategory insight with validation"""
        # UPDATED to use new column name
        likelihood_text = top_sub['Likelihood to spend (vs. Local Gen Pop)']

        if '% More' in likelihood_text:
            try:
                percent = float(likelihood_text.split('%')[0])  # This is 330 (% MORE)

                # No validation - always add the insight
                if percent > 200:
                    # FIX: Calculate multiplier from original PERC_INDEX
                    perc_index = percent + 100  # 330 + 100 = 430
                    multiplier = round(perc_index / 100, 1)  # 430 / 100 = 4.3X

                    insights.append(
                        f"{self.team_short} fans are more than {multiplier}X more likely "
                        f"to spend on {top_sub['Subcategory']} vs. the {self.comparison_pop}"
                    )
                else:
                    insights.append(
                        f"{self.team_short} fans are {likelihood_text} likely to spend on "
                        f"{top_sub['Subcategory']} vs. the {self.comparison_pop}"
                    )
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse likelihood text '{likelihood_text}': {e}")

    def _add_highest_spend_subcategory_insight(self, insights: List[str],
                                               subcategory_df: pd.DataFrame):
        """Add insight about highest SPC subcategory"""
        if subcategory_df.empty:
            return

        # Filter for team fans with valid SPC data
        team_data = subcategory_df[
            (subcategory_df['AUDIENCE'] == self.audience_name) &
            (subcategory_df['SPC'] > 0)
            ]

        if team_data.empty:
            return

        # Find subcategory with highest SPC
        highest_spc_row = team_data.nlargest(1, 'SPC').iloc[0]
        spc_value = float(highest_spc_row['SPC'])
        subcategory_name = self._format_subcategory_name(
            highest_spc_row['SUBCATEGORY'],
            {'is_custom': False}  # Assume fixed for formatting
        )

        # Format the SPC value
        if spc_value >= 1000:
            formatted_spc = f"${spc_value:,.0f}"
        else:
            formatted_spc = f"${spc_value:.2f}"

        insights.append(
            f"{self.team_short} fans spend an average of {formatted_spc} "
            f"per fan per year on {subcategory_name}"
        )

    def _get_league_comparison_subcategory(self, subcategory_df: pd.DataFrame,
                                           category_config: Dict[str, Any]) -> Optional[str]:
        """Find subcategory where team most over-indexes vs NBA Fans within current category across ALL indices"""
        if subcategory_df.empty:
            return None

        # Get category names to filter by
        if category_config.get('is_custom', False):
            category_names = [category_config['display_name']]
        else:
            category_names = category_config.get('category_names_in_data', [])

        # Filter for ONLY subcategories in the current category
        category_filter = subcategory_df['CATEGORY'].isin(category_names)

        # Get subcategories comparing to NBA Fans FOR THIS CATEGORY
        nba_comp = subcategory_df[
            (subcategory_df['AUDIENCE'] == self.audience_name) &
            (subcategory_df['COMPARISON_POPULATION'] == 'NBA Fans') &
            category_filter  # Only subcategories in current category
            ]

        if nba_comp.empty:
            return None

        # Define the indices to check
        index_columns = ['PERC_INDEX', 'SPC_INDEX', 'SPP_INDEX', 'PPC_INDEX', 'COMPOSITE_INDEX']

        # Find the maximum value across all indices and subcategories
        max_value = 0
        best_index_name = None
        best_subcategory = None
        best_row = None

        for _, row in nba_comp.iterrows():
            for index_col in index_columns:
                if index_col in row and pd.notna(row[index_col]):
                    value = float(row[index_col])
                    if value > max_value:
                        max_value = value
                        best_index_name = index_col
                        best_subcategory = row['SUBCATEGORY']
                        best_row = row

        # If no significant value found
        if best_row is None or max_value <= 100:  # 100 means no difference
            return None

        # Calculate the difference (subtract 100 to get "% MORE")
        index_diff = max_value - 100

        # Only report if significant (>5%)
        if index_diff <= self.min_significant_difference:
            return None

        # Format the subcategory name for display
        subcategory_name = self._format_subcategory_name(
            best_subcategory,
            category_config
        )

        # Map index names to more readable descriptions
        index_descriptions = {
            'PERC_INDEX': 'likely to spend',
            'SPC_INDEX': 'spending per customer',
            'SPP_INDEX': 'spending per purchase',
            'PPC_INDEX': 'purchase frequency',
            'COMPOSITE_INDEX': 'overall engagement'
        }

        # Get the description for the winning index
        metric_description = index_descriptions.get(best_index_name, 'engagement')

        # Generate insight based on which index was highest
        if best_index_name == 'PERC_INDEX':
            return (
                f"{self.team_name} fans are {index_diff:.0f}% more likely "
                f"to spend on {subcategory_name} when compared to the NBA average"
            )
        elif best_index_name == 'SPC_INDEX':
            return (
                f"{self.team_name} fans have {index_diff:.0f}% higher spending per customer "
                f"on {subcategory_name} when compared to the NBA average"
            )
        elif best_index_name == 'SPP_INDEX':
            return (
                f"{self.team_name} fans spend {index_diff:.0f}% more per purchase "
                f"on {subcategory_name} when compared to the NBA average"
            )
        elif best_index_name == 'PPC_INDEX':
            return (
                f"{self.team_name} fans make {index_diff:.0f}% more purchases "
                f"of {subcategory_name} when compared to the NBA average"
            )
        else:  # COMPOSITE_INDEX
            return (
                f"{self.team_name} fans show {index_diff:.0f}% higher overall engagement "
                f"with {subcategory_name} when compared to the NBA average"
            )

    def _get_standardized_name_from_table(self, merchant_name: str, merchant_table: pd.DataFrame) -> str:
        """
        Get the standardized merchant name from the table

        Args:
            merchant_name: Original or standardized merchant name to look up
            merchant_table: DataFrame with standardized names in 'Brand' column

        Returns:
            Standardized merchant name from the table, or original if not found
        """
        # First try exact match with the standardized names in the table
        exact_match = merchant_table[merchant_table['Brand'] == merchant_name]
        if not exact_match.empty:
            return merchant_name  # Already standardized

        # If not found, the merchant_name might be the original name
        # We need to find it by looking at the MERCHANT_ORIGINAL column in our data
        if hasattr(self, 'raw_data') and 'merchant' in self.raw_data:
            merchant_df = self.raw_data['merchant']

            # Look for rows where MERCHANT_ORIGINAL matches
            if 'MERCHANT_ORIGINAL' in merchant_df.columns:
                matching_rows = merchant_df[merchant_df['MERCHANT_ORIGINAL'] == merchant_name]
                if not matching_rows.empty:
                    # Return the standardized name
                    standardized_name = matching_rows.iloc[0]['MERCHANT']
                    return standardized_name

        # Fallback: try to find by partial match in the table
        for _, row in merchant_table.iterrows():
            brand = row['Brand']
            # Simple check for similarity (remove punctuation and compare)
            if merchant_name.replace("'", "").replace("-", "").upper() == brand.replace("'", "").replace("-",
                                                                                                         "").upper():
                return brand

        # If all else fails, return the original name
        return merchant_name

    def _generate_merchant_insights(self, merchant_stats: Tuple[pd.DataFrame, List[str]],
                                    merchant_df: pd.DataFrame,
                                    merchant_last_year_df: pd.DataFrame = None) -> List[str]:
        """
        FIXED: Generate merchant-specific insights ensuring consistent standardized names
        """
        merchant_table, top_merchants = merchant_stats
        insights = []

        if merchant_table.empty or not top_merchants:
            return insights

        # 1. Top merchant by audience percentage (USE STANDARDIZED NAME FROM TABLE)
        top_merchant = merchant_table.iloc[0]
        insights.append(
            f"{top_merchant['Percent of Fans Who Spend']} of {self.team_name} fans "
            f"spent at {top_merchant['Brand']}"  # USE Brand from table (standardized)
        )

        # 2. Find merchant with highest PPC - NOW USES LAST_FULL_YEAR if available
        if merchant_last_year_df is not None and not merchant_last_year_df.empty:
            highest_ppc_merchant = self._find_highest_ppc_merchant(merchant_last_year_df, top_merchants)
        else:
            highest_ppc_merchant = self._find_highest_ppc_merchant(merchant_df, top_merchants)

        if highest_ppc_merchant:
            # GET STANDARDIZED NAME FROM TABLE instead of raw data
            standardized_name = self._get_standardized_name_from_table(
                highest_ppc_merchant['merchant'], merchant_table
            )

            insights.append(
                f"{self.team_name} fans make an average of {highest_ppc_merchant['ppc']:.0f} "
                f"purchases per year at {standardized_name}"
            )

        # 3. Find merchant with highest SPC - NOW USES LAST_FULL_YEAR if available
        if merchant_last_year_df is not None and not merchant_last_year_df.empty:
            highest_spc_merchant = self._find_highest_spc_merchant(merchant_last_year_df, top_merchants)
        else:
            highest_spc_merchant = self._find_highest_spc_merchant(merchant_df, top_merchants)

        if highest_spc_merchant:
            spc_value = highest_spc_merchant['spc']
            if spc_value >= 1000:
                formatted_spc = f"${spc_value:,.0f}"
            else:
                formatted_spc = f"${spc_value:.2f}"

            # GET STANDARDIZED NAME FROM TABLE instead of raw data
            standardized_name = self._get_standardized_name_from_table(
                highest_spc_merchant['merchant'], merchant_table
            )

            insights.append(
                f"{self.team_name} fans spent an average of {formatted_spc} per fan "
                f"on {standardized_name} per year"
            )

        # 4. Best NBA/League comparison - continues to use ALL_TIME data
        best_nba_merchant = self._find_best_nba_comparison(merchant_df, top_merchants)
        if best_nba_merchant:
            # GET STANDARDIZED NAME FROM TABLE instead of raw data
            standardized_name = self._get_standardized_name_from_table(
                best_nba_merchant['merchant'], merchant_table
            )

            insights.append(
                f"{self.team_name} fans are {best_nba_merchant['index_diff']:.0f}% more likely "
                f"to spend on {standardized_name} than {self.league} fans"
            )

        return insights

    def _find_highest_ppc_merchant(self, merchant_df: pd.DataFrame,
                                   top_merchants: List[str]) -> Optional[Dict[str, Any]]:
        """Find merchant with highest purchases per customer (uses standardized names)"""
        if merchant_df.empty:
            return None

        # Filter for team fans and top merchants
        filtered_df = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['MERCHANT'].isin(top_merchants))  # MERCHANT now has standardized names
            ]

        if filtered_df.empty:
            return None

        # Find merchant with highest PPC
        highest_ppc_row = filtered_df.nlargest(1, 'PPC').iloc[0]

        return {
            'merchant': highest_ppc_row['MERCHANT'],  # Returns standardized name
            'ppc': float(highest_ppc_row['PPC'])
        }

    def _find_highest_spc_merchant(self, merchant_df: pd.DataFrame,
                                   top_merchants: List[str]) -> Optional[Dict[str, Any]]:
        """Find merchant with highest spend per customer (uses standardized names)"""
        if merchant_df.empty:
            return None

        # Filter for team fans and top merchants
        filtered_df = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['MERCHANT'].isin(top_merchants)) &  # MERCHANT now has standardized names
            (merchant_df['SPC'] > 0)  # Ensure valid SPC
            ]

        if filtered_df.empty:
            return None

        # Find merchant with highest SPC
        highest_spc_row = filtered_df.nlargest(1, 'SPC').iloc[0]

        return {
            'merchant': highest_spc_row['MERCHANT'],  # Returns standardized name
            'spc': float(highest_spc_row['SPC'])
        }

    def _find_best_nba_comparison(self, merchant_df: pd.DataFrame,
                                  top_merchants: List[str]) -> Optional[Dict[str, Any]]:
        """Find merchant with best NBA/League comparison (uses standardized names)"""
        if merchant_df.empty:
            return None

        # Filter for team fans comparing to NBA/League fans
        nba_comp = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['COMPARISON_POPULATION'] == self.league_fans) &
            (merchant_df['MERCHANT'].isin(top_merchants))  # MERCHANT now has standardized names
            ]

        if nba_comp.empty:
            return None

        # Find merchant with highest PERC_INDEX
        best_merchant = nba_comp.nlargest(1, 'PERC_INDEX').iloc[0]

        # Calculate index difference
        index_diff = float(best_merchant['PERC_INDEX'])

        # Only report if significant
        if index_diff > self.min_significant_difference:
            return {
                'merchant': best_merchant['MERCHANT'],  # Returns standardized name
                'index_diff': index_diff
            }

        return None

    def _get_sponsorship_recommendation(self, merchant_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate sponsorship recommendation based on composite index (with standardized names)"""
        if merchant_df.empty:
            return {}

        # Filter for team fans
        team_data = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['COMPOSITE_INDEX'] > 0)
            ]

        if team_data.empty:
            return {}

        # Find merchant with highest composite index
        best_merchant = team_data.nlargest(1, 'COMPOSITE_INDEX').iloc[0]
        merchant_name = best_merchant['MERCHANT']  # Now returns standardized name
        composite_index = float(best_merchant['COMPOSITE_INDEX'])

        # Generate recommendation text (now with standardized name)
        main_recommendation = (
            f"The {self.team_short} should target {merchant_name} for a sponsorship "
            f"based on having the highest composite index of {composite_index:.0f}"
        )

        # Sub-explanation
        sub_explanation = (
            "The composite index indicates a brand with significant likelihood "
            "for more fans to be spending more frequently, and at a higher spend "
            "per fan vs. other brands"
        )

        return {
            'merchant': merchant_name,  # Now standardized name
            'composite_index': composite_index,
            'explanation': main_recommendation,
            'sub_explanation': sub_explanation,
            'full_recommendation': {
                'main': main_recommendation,
                'sub_bullet': sub_explanation
            }
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
        """Format subcategory name for display with custom overrides"""
        # UPDATED: First check if there's a custom override
        if subcategory in self.subcategory_overrides:
            return self.subcategory_overrides[subcategory]

        # For custom categories, just clean up the name
        if category_config.get('is_custom', False):
            # Remove category prefix if it exists
            category_name = category_config.get('display_name', '')
            if subcategory.startswith(f"{category_name} - "):
                return subcategory.replace(f"{category_name} - ", "")
            return subcategory

        # For fixed categories, strip the prefix by looking for " - "
        if " - " in subcategory:
            # Get everything after the first " - "
            return subcategory.split(" - ", 1)[1]

        return subcategory

    def _verify_merchant_threshold(self, category_name: str, merchant_df: pd.DataFrame, threshold: float) -> bool:
        """
        Check if any merchant in category meets audience threshold

        Args:
            category_name: Category name to check
            merchant_df: DataFrame with merchant data
            threshold: Minimum PERC_AUDIENCE threshold (e.g., 0.10 for 10%)

        Returns:
            True if at least one merchant meets threshold, False otherwise
        """
        if merchant_df.empty:
            return False

        # FIXED: Strip whitespace from both the input category name and the DataFrame values
        category_name_clean = category_name.strip()

        # Filter for merchants in this category for team fans
        # Strip whitespace from CATEGORY column values for comparison
        category_merchants = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['CATEGORY'].str.strip() == category_name_clean)
            ]

        if category_merchants.empty:
            logger.debug(f"No merchants found for category '{category_name}' (cleaned: '{category_name_clean}') "
                         f"and audience '{self.audience_name}'")
            return False

        # Check if any merchant has audience percentage above threshold
        max_merchant_audience = category_merchants['PERC_AUDIENCE'].max()

        # Log the result for debugging
        if max_merchant_audience >= threshold:
            top_merchant = category_merchants.loc[category_merchants['PERC_AUDIENCE'].idxmax()]
            logger.info(f"  ✓ Category '{category_name}' has merchant '{top_merchant['MERCHANT']}' "
                        f"with {max_merchant_audience * 100:.1f}% audience")

        return max_merchant_audience >= threshold

    def get_custom_categories(self,
                              category_df: pd.DataFrame,
                              merchant_df: pd.DataFrame,  # NEW: Add merchant data
                              is_womens_team: bool = False,
                              existing_categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get custom categories using tiered selection approach
        - Established categories (slots 1-3): 20% category + 10% merchant thresholds
        - Emerging category (slot 4, men's only): 10% category, no merchant requirement

        Args:
            category_df: DataFrame with category-level data
            merchant_df: DataFrame with merchant-level data for verification
            is_womens_team: Whether this is a women's team
            existing_categories: List of already-selected category keys

        Returns:
            List of selected custom categories with metadata
        """
        # Get configuration
        custom_config = self.config.get('custom_category_config', {})
        team_config = custom_config.get('womens_teams' if is_womens_team else 'mens_teams', {})

        # Get tier-specific settings
        established_config = team_config.get('established_categories', {})
        emerging_config = team_config.get('emerging_category', {})

        # Extract thresholds
        established_count = established_config.get('count', 3 if not is_womens_team else 2)
        established_cat_threshold = established_config.get('min_audience_pct', 0.20)
        established_merch_threshold = established_config.get('min_merchant_audience_pct', 0.10)

        emerging_count = emerging_config.get('count', 1 if not is_womens_team else 0)
        emerging_cat_threshold = emerging_config.get('min_audience_pct', 0.10)

        # Default existing categories if not provided
        if existing_categories is None:
            existing_fixed = (self.config['fixed_categories']['womens_teams'] if is_womens_team
                              else self.config['fixed_categories']['mens_teams'])
            existing_categories = existing_fixed

        # Get category names already used in fixed categories
        category_names_to_exclude = []
        for cat_key in existing_categories:
            if cat_key in self.categories:
                category_names_to_exclude.extend(
                    self.categories[cat_key].get('category_names_in_data', [])
                )

        # Base filter: team fans with correct comparison population
        base_filter = (
                (category_df['AUDIENCE'] == self.audience_name) &
                (category_df['COMPARISON_POPULATION'] == self.comparison_pop)
        )

        # PASS 1: Find established categories (high thresholds + merchant verification)
        established_candidates = category_df[
            base_filter &
            (category_df['PERC_AUDIENCE'] >= established_cat_threshold) &
            (category_df['CATEGORY'].isin(self.allowed_custom)) &
            (~category_df['CATEGORY'].isin(self.excluded_custom)) &
            (~category_df['CATEGORY'].isin(category_names_to_exclude))
            ].copy()

        # Verify merchant threshold for each candidate
        established_categories = []

        if not established_candidates.empty:
            # Sort by composite index
            established_candidates = established_candidates.sort_values('COMPOSITE_INDEX', ascending=False)

            for _, row in established_candidates.iterrows():
                if len(established_categories) >= established_count:
                    break

                category_name = row['CATEGORY']

                # Verify at least one merchant meets threshold
                if self._verify_merchant_threshold(category_name, merchant_df, established_merch_threshold):
                    category_info = {
                        'category_key': category_name.lower().replace(' ', '_').replace('-', '_'),
                        'display_name': category_name,
                        'category_names_in_data': [category_name],
                        'composite_index': float(row['COMPOSITE_INDEX']),
                        'audience_pct': float(row['PERC_AUDIENCE']),
                        'perc_index': float(row['PERC_INDEX']),
                        'is_custom': True,
                        'is_emerging': False  # NEW: Mark as established
                    }
                    established_categories.append(category_info)
                    logger.info(f"✓ Selected established category: {category_name} "
                                f"(composite: {category_info['composite_index']:.1f}, "
                                f"audience: {category_info['audience_pct'] * 100:.1f}%)")
                else:
                    logger.info(
                        f"✗ Skipped {category_name} - no merchant meets {established_merch_threshold * 100:.0f}% threshold")

        # PASS 2: Find emerging category (relaxed thresholds, no merchant requirement)
        emerging_categories = []

        if emerging_count > 0 and not is_womens_team:
            # Get categories already selected as established
            selected_category_names = [cat['display_name'] for cat in established_categories]

            emerging_candidates = category_df[
                base_filter &
                (category_df['PERC_AUDIENCE'] >= emerging_cat_threshold) &
                (category_df['CATEGORY'].isin(self.allowed_custom)) &
                (~category_df['CATEGORY'].isin(self.excluded_custom)) &
                (~category_df['CATEGORY'].isin(category_names_to_exclude)) &
                (~category_df['CATEGORY'].isin(selected_category_names))  # Exclude already selected
                ].copy()

            if not emerging_candidates.empty:
                # Get the highest composite index category
                top_emerging = emerging_candidates.nlargest(1, 'COMPOSITE_INDEX').iloc[0]
                category_name = top_emerging['CATEGORY']

                category_info = {
                    'category_key': category_name.lower().replace(' ', '_').replace('-', '_'),
                    'display_name': category_name,
                    'category_names_in_data': [category_name],
                    'composite_index': float(top_emerging['COMPOSITE_INDEX']),
                    'audience_pct': float(top_emerging['PERC_AUDIENCE']),
                    'perc_index': float(top_emerging['PERC_INDEX']),
                    'is_custom': True,
                    'is_emerging': True  # NEW: Mark as emerging
                }
                emerging_categories.append(category_info)
                logger.info(f"★ Selected emerging category: {category_name} "
                            f"(composite: {category_info['composite_index']:.1f}, "
                            f"audience: {category_info['audience_pct'] * 100:.1f}%)")

        # Combine results
        all_custom_categories = established_categories + emerging_categories

        # Log summary
        logger.info(f"\nCustom category selection complete:")
        logger.info(f"  - Established categories: {len(established_categories)}")
        logger.info(f"  - Emerging categories: {len(emerging_categories)}")
        logger.info(f"  - Total selected: {len(all_custom_categories)}")

        return all_custom_categories

    def create_custom_category_config(self, category_name: str) -> Dict[str, Any]:
        """
        Create a category configuration for a custom category

        Args:
            category_name: Name of the category from the data

        Returns:
            Category configuration similar to what's in category_config.yaml
        """
        # First, check if we have a predefined config for this category
        # Try the lowercase version as a key
        category_key = category_name.lower().replace(' ', '_').replace('-', '_')

        if category_key in self.categories:
            # Use the predefined configuration
            predefined_config = self.categories[category_key].copy()
            predefined_config['is_custom'] = True  # Mark it as custom for processing
            logger.info(f"Using predefined config for custom category: {category_name}")
            return predefined_config

        # Otherwise, generate a default configuration
        logger.info(f"Generating default config for custom category: {category_name}")
        slide_title = f"{category_name} Sponsor Analysis"

        config = {
            'display_name': category_name,
            'slide_title': slide_title,
            'category_names_in_data': [category_name],
            'subcategories': {
                'include': [],
                'exclude': []
            },
            'is_custom': True
        }

        return config