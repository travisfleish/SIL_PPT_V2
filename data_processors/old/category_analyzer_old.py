# data_processors/category_analyzer.py
"""
Category analyzer that processes spending data by category
Generates insights and recommendations for sponsorship opportunities
OPTIMIZED to only standardize merchants that will be used in presentation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
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
    """OPTIMIZED: Analyzes category spending data with selective merchant name standardization"""

    def __init__(self, team_name: str, team_short: str, league: str,
                 config_path: Optional[Path] = None,
                 comparison_population: str = None,
                 cache_manager: Optional[Any] = None):
        """
        Initialize the category analyzer with merchant name standardization

        Args:
            team_name: Full team name (e.g., "Utah Jazz")
            team_short: Short team name (e.g., "Jazz")
            league: League name (e.g., "NBA")
            config_path: Path to categories config file
            comparison_population: Comparison population string
            cache_manager: Optional CacheManager instance for caching
        """
        self.team_name = team_name
        self.team_short = team_short
        self.league = league
        self.cache_manager = cache_manager

        # Standard audiences
        self.audience_name = f"{team_name} Fans"
        if comparison_population:
            self.comparison_pop = comparison_population
        else:
            self.comparison_pop = f"Local Gen Pop (Excl. {team_short})"
        self.league_fans = f"{league} Fans"

        # Initialize merchant name standardizer
        try:
            from utils.merchant_name_standardizer import MerchantNameStandardizer
            self.standardizer = MerchantNameStandardizer(
                cache_enabled=True,
                cache_manager=self.cache_manager
            )
            logger.info("✅ CategoryAnalyzer: Merchant name standardization enabled")

            if self.cache_manager:
                logger.info("  Using PostgreSQL cache for merchant names")
            else:
                logger.info("  Using file cache for merchant names")

        except ImportError:
            logger.warning("⚠️ CategoryAnalyzer: MerchantNameStandardizer not available")
            self.standardizer = None

        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent / 'config' / 'categories.yaml'

        if not config_path.exists():
            config_path = Path.cwd() / 'config' / 'categories.yaml'

        if not config_path.exists():
            raise FileNotFoundError(f"Could not find categories.yaml")

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.categories = self.config['categories']
        self.excluded_custom = self.config['excluded_from_custom']
        self.allowed_custom = self.config.get('allowed_for_custom', [])
        self.subcategory_overrides = self.config.get('subcategory_name_overrides', {})

        # Validation thresholds
        self.max_reasonable_index = 1000
        self.min_significant_difference = 0

    def analyze_category(self,
                         category_key: str,
                         category_df: pd.DataFrame,
                         subcategory_df: pd.DataFrame,
                         merchant_df: pd.DataFrame,
                         subcategory_last_year_df: pd.DataFrame = None,
                         merchant_last_year_df: pd.DataFrame = None,
                         validate: bool = True) -> Dict[str, Any]:
        """
        OPTIMIZED: Analyze category with selective merchant standardization
        """
        # Get category configuration
        category_config = self.categories.get(category_key)
        if not category_config:
            raise ValueError(f"Unknown category: {category_key}")

        # Clean data
        for df in [category_df, subcategory_df, merchant_df, subcategory_last_year_df, merchant_last_year_df]:
            if df is not None and not df.empty:
                self._clean_dataframe(df)

        # Filter merchant data based on subcategory exclusions/inclusions
        filtered_merchant_df = self._filter_merchants_by_subcategory(merchant_df, subcategory_df, category_config)
        filtered_merchant_last_year_df = None
        if merchant_last_year_df is not None and not merchant_last_year_df.empty:
            filtered_merchant_last_year_df = self._filter_merchants_by_subcategory(
                merchant_last_year_df, subcategory_last_year_df, category_config
            )

        # OPTIMIZATION: First identify which merchants we'll actually use (from filtered data)
        merchants_to_standardize = self._identify_merchants_to_standardize(
            filtered_merchant_df,
            filtered_merchant_last_year_df
        )

        logger.info(f"🎯 Identified {len(merchants_to_standardize)} merchants to standardize "
                    f"(out of {len(filtered_merchant_df['MERCHANT'].unique()) if not filtered_merchant_df.empty else 0} filtered merchants)")

        # OPTIMIZATION: Only standardize the merchants we need
        if merchants_to_standardize and self.standardizer:
            filtered_merchant_df = self._standardize_selected_merchants(filtered_merchant_df, merchants_to_standardize)
            if filtered_merchant_last_year_df is not None and not filtered_merchant_last_year_df.empty:
                filtered_merchant_last_year_df = self._standardize_selected_merchants(
                    filtered_merchant_last_year_df, merchants_to_standardize
                )

        # Store raw data for validation (AFTER selective standardization)
        self.raw_data = {
            'category': category_df,
            'subcategory': subcategory_df,
            'merchant': filtered_merchant_df,  # Store filtered version
            'merchant_original': merchant_df,  # Keep original for reference
            'subcategory_last_year': subcategory_last_year_df,
            'merchant_last_year': filtered_merchant_last_year_df
        }

        # Continue with analysis
        category_metrics = self._get_category_metrics(category_df, category_config)

        if validate:
            metric_issues = category_metrics.validate()
            if metric_issues:
                logger.warning(f"Metric validation issues: {metric_issues}")

        subcategory_stats = self._get_subcategory_stats(subcategory_df, category_config)

        insights = self._generate_insights(
            category_config, category_metrics, subcategory_stats,
            category_df, subcategory_df, subcategory_last_year_df
        )

        # Use filtered merchant data for all merchant analysis
        merchant_stats = self._get_merchant_stats(filtered_merchant_df)
        merchant_insights = self._generate_merchant_insights(
            merchant_stats, filtered_merchant_df, filtered_merchant_last_year_df
        )

        recommendation = self._get_sponsorship_recommendation(filtered_merchant_df)

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

    def _identify_merchants_to_standardize(self,
                                           merchant_df: pd.DataFrame,
                                           merchant_last_year_df: pd.DataFrame = None) -> Set[str]:
        """
        OPTIMIZATION: Pre-identify which merchants will be used in the presentation

        Returns:
            Set of merchant names that need standardization
        """
        merchants_needed = set()

        if merchant_df.empty:
            return merchants_needed

        # 1. Top 5 merchants by audience percentage (for merchant table)
        team_data = merchant_df[merchant_df['AUDIENCE'] == self.audience_name]
        if not team_data.empty:
            top_5_by_audience = (team_data
                                 .sort_values('PERC_AUDIENCE', ascending=False)
                                 .drop_duplicates('MERCHANT')
                                 .head(5)['MERCHANT'].tolist())
            merchants_needed.update(top_5_by_audience)
            logger.debug(f"  Top 5 by audience: {top_5_by_audience}")

        # 2. Top merchant by composite index (for recommendation)
        rec_data = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['COMPARISON_POPULATION'] == self.comparison_pop) &
            (merchant_df['COMPOSITE_INDEX'] > 0) &
            (merchant_df['PERC_AUDIENCE'] >= 0.01)
            ]
        if not rec_data.empty:
            top_composite = rec_data.nlargest(1, 'COMPOSITE_INDEX')['MERCHANT'].iloc[0]
            merchants_needed.add(top_composite)
            logger.debug(f"  Top by composite index: {top_composite}")

        # 3. Check LAST_FULL_YEAR data for highest PPC/SPC merchants
        if merchant_last_year_df is not None and not merchant_last_year_df.empty and top_5_by_audience:
            last_year_team = merchant_last_year_df[
                (merchant_last_year_df['AUDIENCE'] == self.audience_name) &
                (merchant_last_year_df['MERCHANT'].isin(top_5_by_audience))
                ]

            if not last_year_team.empty:
                # Highest PPC
                if 'PPC' in last_year_team.columns:
                    highest_ppc = last_year_team.nlargest(1, 'PPC')
                    if not highest_ppc.empty:
                        merchants_needed.add(highest_ppc['MERCHANT'].iloc[0])

                # Highest SPC
                if 'SPC' in last_year_team.columns and (last_year_team['SPC'] > 0).any():
                    highest_spc = last_year_team[last_year_team['SPC'] > 0].nlargest(1, 'SPC')
                    if not highest_spc.empty:
                        merchants_needed.add(highest_spc['MERCHANT'].iloc[0])

        # 4. Best NBA comparison merchant (among top 5)
        if top_5_by_audience:
            nba_comp = merchant_df[
                (merchant_df['AUDIENCE'] == self.audience_name) &
                (merchant_df['COMPARISON_POPULATION'] == self.league_fans) &
                (merchant_df['MERCHANT'].isin(top_5_by_audience))
                ]
            if not nba_comp.empty:
                best_nba = nba_comp.nlargest(1, 'PERC_INDEX')
                if not best_nba.empty and float(best_nba['PERC_INDEX'].iloc[0]) > 100:
                    merchants_needed.add(best_nba['MERCHANT'].iloc[0])

        return merchants_needed

    def _standardize_selected_merchants(self,
                                        df: pd.DataFrame,
                                        merchants_to_standardize: Set[str]) -> pd.DataFrame:
        """
        OPTIMIZATION: Only standardize specific merchants instead of all

        Args:
            df: DataFrame with MERCHANT column
            merchants_to_standardize: Set of merchant names to standardize

        Returns:
            DataFrame with selected merchants standardized
        """
        if 'MERCHANT' not in df.columns or df.empty or not merchants_to_standardize:
            return df

        try:
            # Create a copy to avoid modifying original
            df = df.copy()

            # Preserve original names
            df['MERCHANT_ORIGINAL'] = df['MERCHANT'].copy()

            # Convert set to list for API call
            merchants_list = list(merchants_to_standardize)

            logger.info(f"🔄 Standardizing {len(merchants_list)} selected merchants...")

            # Get standardized mapping for ONLY the merchants we need
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                name_mapping = loop.run_until_complete(
                    self.standardizer.standardize_merchants(merchants_list)
                )
            finally:
                loop.close()

            # Apply mapping ONLY to the rows with these merchants
            for original, standardized in name_mapping.items():
                df.loc[df['MERCHANT'] == original, 'MERCHANT'] = standardized

            logger.info(f"✅ Standardized {len(name_mapping)} merchant names")

            # Log performance stats
            if hasattr(self.standardizer, 'log_performance'):
                self.standardizer.log_performance()

            return df

        except Exception as e:
            logger.warning(f"⚠️ Merchant standardization failed: {e}")
            return df

    def _clean_dataframe(self, df: pd.DataFrame):
        """Clean dataframe in place"""
        string_cols = df.select_dtypes(include=['object']).columns
        for col in string_cols:
            if col in df.columns:
                df.loc[:, col] = df[col].astype(str).str.strip()

        if 'AUDIENCE' in df.columns:
            df.dropna(subset=['AUDIENCE'], inplace=True)

    def _filter_merchants_by_subcategory(self, merchant_df: pd.DataFrame,
                                         subcategory_df: pd.DataFrame,
                                         category_config: Dict[str, Any]) -> pd.DataFrame:
        """
        Filter merchants based on subcategory inclusion/exclusion rules
        """
        if merchant_df.empty:
            return merchant_df

        # Get subcategory configuration
        subcategory_config = category_config.get('subcategories', {})
        included = subcategory_config.get('include', [])
        excluded = subcategory_config.get('exclude', [])

        # If no filtering rules, return original
        if not included and not excluded:
            return merchant_df

        # If SUBCATEGORY column exists in merchant data, use it directly
        if 'SUBCATEGORY' in merchant_df.columns:
            filtered_df = merchant_df.copy()

            if included:
                # Get all included subcategory names
                included_names = []
                for sub in included:
                    if isinstance(sub, dict):
                        key_in_data = sub.get('key_in_data', '')
                        if isinstance(key_in_data, list):
                            included_names.extend(key_in_data)
                        else:
                            included_names.append(key_in_data)
                    else:
                        included_names.append(sub)

                # Filter to only included subcategories
                before_count = len(filtered_df)
                filtered_df = filtered_df[filtered_df['SUBCATEGORY'].isin(included_names)]
                after_count = len(filtered_df)
                logger.info(f"Filtered merchants to {len(included_names)} included subcategories "
                            f"({before_count} → {after_count} records)")

            elif excluded:
                # Filter out excluded subcategories
                before_count = len(filtered_df)
                filtered_df = filtered_df[~filtered_df['SUBCATEGORY'].isin(excluded)]
                after_count = len(filtered_df)

                # Log what was actually excluded
                excluded_count = before_count - after_count
                if excluded_count > 0:
                    logger.info(f"Excluded {excluded_count} merchant records from subcategories: {excluded}")

                    # Show which merchants were excluded (for debugging)
                    excluded_merchants = merchant_df[merchant_df['SUBCATEGORY'].isin(excluded)]
                    if not excluded_merchants.empty:
                        unique_excluded = excluded_merchants['MERCHANT'].nunique()
                        logger.info(f"  Removed {unique_excluded} unique merchants")

                        # Log specific subcategory counts
                        for subcat in excluded:
                            subcat_count = len(merchant_df[merchant_df['SUBCATEGORY'] == subcat])
                            if subcat_count > 0:
                                logger.info(f"  - {subcat}: {subcat_count} records")

            return filtered_df

        # If SUBCATEGORY column doesn't exist in merchant_df
        else:
            logger.warning("SUBCATEGORY column not found in merchant_df - unable to filter by subcategory")
            logger.info("Available columns in merchant_df: " + ", ".join(merchant_df.columns.tolist()))

            # Return original dataframe since we can't filter without subcategory info
            return merchant_df

    def _get_category_metrics(self, df: pd.DataFrame,
                              category_config: Dict[str, Any]) -> CategoryMetrics:
        """Extract category-level metrics"""
        if df.empty:
            logger.warning(f"No category data found")
            return CategoryMetrics(0, 0, 0, 0, 0, 0, 0, self.comparison_pop)

        comp_data = df[
            (df['AUDIENCE'] == self.audience_name) &
            (df['COMPARISON_POPULATION'] == self.comparison_pop)
            ]

        if comp_data.empty:
            logger.warning(f"No comparison data found for {self.comparison_pop}")
            return CategoryMetrics(0, 0, 0, 0, 0, 0, 0, self.comparison_pop)

        row = comp_data.iloc[0]
        percent_fans = float(row['PERC_AUDIENCE'])
        percent_likely = float(row['PERC_INDEX']) - 100

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

        team_data = df[
            (df['AUDIENCE'] == self.audience_name) &
            (df['COMPARISON_POPULATION'] == self.comparison_pop)
            ].copy()

        if team_data.empty:
            return pd.DataFrame()

        is_custom = category_config.get('is_custom', False)

        if is_custom:
            logger.info(f"Processing custom category {category_config.get('display_name')}")
            team_data = team_data[team_data['SUBCATEGORY'].notna()]
        else:
            subcategory_config = category_config.get('subcategories', {})
            included = subcategory_config.get('include', [])
            excluded = subcategory_config.get('exclude', [])

            if included:
                included_names = [sub['key_in_data'] if isinstance(sub, dict) else sub
                                  for sub in included]
                all_included = []
                for name in included_names:
                    if isinstance(name, list):
                        all_included.extend(name)
                    else:
                        all_included.append(name)
                team_data = team_data[team_data['SUBCATEGORY'].isin(all_included)]
            elif excluded:
                team_data = team_data[~team_data['SUBCATEGORY'].isin(excluded)]

        if team_data.empty:
            return pd.DataFrame()

        top_subcategories = team_data.nlargest(4, 'COMPOSITE_INDEX')

        results = []
        for _, row in top_subcategories.iterrows():
            percent_fans = float(row['PERC_AUDIENCE']) * 100
            percent_likely = float(row['PERC_INDEX']) - 100
            percent_purch = self._calculate_percent_diff(
                float(row['PPC']),
                float(row['COMPARISON_PPC'])
            )

            subcategory_name = self._format_subcategory_name(
                row['SUBCATEGORY'], category_config
            )

            results.append({
                'Subcategory': subcategory_name,
                'Percent of Fans Who Spend': f"{percent_fans:.0f}%",
                'Likelihood to spend (vs. Local Gen Pop)':
                    f"{abs(percent_likely):.0f}% {'More' if percent_likely > 0 else 'Less'}",
                'Purchases Per Fan (vs. Gen Pop)':
                    f"{abs(percent_purch):.0f}% {'More' if percent_purch > 0 else 'Less'}"
            })

        return pd.DataFrame(results)

    def _get_merchant_stats(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Get top merchant statistics (now with standardized names)"""
        if df.empty:
            return pd.DataFrame(), []

        team_data = df[df['AUDIENCE'] == self.audience_name]

        if team_data.empty:
            return pd.DataFrame(), []

        top_5_merchants = (team_data
                           .sort_values('PERC_AUDIENCE', ascending=False)
                           .drop_duplicates('MERCHANT')
                           .head(5)['MERCHANT'].tolist())

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
                    'Likelihood to spend (vs. Local Gen Pop)':
                        f"{abs(percent_likely):.0f}% {'More' if percent_likely >= 0 else 'Less'}",
                    'Purchases Per Fan (vs. Gen Pop)':
                        f"{abs(ppc_diff):.0f}% {'More' if ppc_diff >= 0 else 'Less'}"
                })

        if results:
            merchant_df = pd.DataFrame(results)
            merchant_df['Rank'] = range(1, len(merchant_df) + 1)

            cols = ['Rank', 'Brand', 'Percent of Fans Who Spend',
                    'Likelihood to spend (vs. Local Gen Pop)',
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

        insights.append(
            f"{self.team_short} fans are {abs(metrics.percent_likely):.0f}% "
            f"{'MORE' if metrics.percent_likely > 0 else 'LESS'} likely to spend on "
            f"{category_config['display_name']} than the {self.comparison_pop}"
        )

        insights.append(
            f"{self.team_short} fans make an average of {abs(metrics.percent_purchases):.0f}% "
            f"{'more' if metrics.percent_purchases > 0 else 'fewer'} purchases per fan on "
            f"{category_config['display_name']} than the {self.comparison_pop}"
        )

        if not subcategory_stats.empty:
            top_sub = subcategory_stats.iloc[0]
            self._add_subcategory_insight(insights, top_sub)

        if subcategory_last_year_df is not None and not subcategory_last_year_df.empty:
            self._add_highest_spend_subcategory_insight(insights, subcategory_last_year_df)
        else:
            self._add_highest_spend_subcategory_insight(insights, subcategory_df)

        nba_insight = self._get_league_comparison_subcategory(subcategory_df, category_config)
        if nba_insight:
            insights.append(nba_insight)

        return insights

    def _add_subcategory_insight(self, insights: List[str], top_sub: pd.Series):
        """Add subcategory insight with validation"""
        likelihood_text = top_sub['Likelihood to spend (vs. Local Gen Pop)']

        if '% More' in likelihood_text:
            try:
                percent = float(likelihood_text.split('%')[0])

                if percent > 200:
                    perc_index = percent + 100
                    multiplier = round(perc_index / 100, 1)

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

        team_data = subcategory_df[
            (subcategory_df['AUDIENCE'] == self.audience_name) &
            (subcategory_df['SPC'] > 0)
            ]

        if team_data.empty:
            return

        highest_spc_row = team_data.nlargest(1, 'SPC').iloc[0]
        spc_value = float(highest_spc_row['SPC'])
        subcategory_name = self._format_subcategory_name(
            highest_spc_row['SUBCATEGORY'],
            {'is_custom': False}
        )

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
        """Find subcategory where team most over-indexes vs NBA Fans"""
        if subcategory_df.empty:
            return None

        # Get NBA comparison data first
        nba_comp = subcategory_df[
            (subcategory_df['AUDIENCE'] == self.audience_name) &
            (subcategory_df['COMPARISON_POPULATION'] == self.league_fans)
            ]

        if nba_comp.empty:
            return None

        # Now apply subcategory filtering based on category config
        subcategory_config = category_config.get('subcategories', {})
        included = subcategory_config.get('include', [])
        excluded = subcategory_config.get('exclude', [])

        # Filter the NBA comparison data
        if included:
            # Get all included subcategory names
            included_names = []
            for sub in included:
                if isinstance(sub, dict):
                    key_in_data = sub.get('key_in_data', '')
                    if isinstance(key_in_data, list):
                        included_names.extend(key_in_data)
                    else:
                        included_names.append(key_in_data)
                else:
                    included_names.append(sub)

            # Filter to only included subcategories
            nba_comp = nba_comp[nba_comp['SUBCATEGORY'].isin(included_names)]
            logger.debug(f"League comparison: Filtered to {len(included_names)} included subcategories")

        elif excluded:
            # Filter out excluded subcategories
            nba_comp = nba_comp[~nba_comp['SUBCATEGORY'].isin(excluded)]
            logger.debug(f"League comparison: Excluded subcategories: {excluded}")

        # If no data left after filtering, return None
        if nba_comp.empty:
            logger.debug("League comparison: No data after subcategory filtering")
            return None

        # Continue with finding the best index
        index_columns = ['PERC_INDEX', 'SPC_INDEX', 'SPP_INDEX', 'PPC_INDEX', 'COMPOSITE_INDEX']

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

        if best_row is None or max_value <= 100:
            return None

        index_diff = max_value - 100

        if index_diff <= self.min_significant_difference:
            return None

        subcategory_name = self._format_subcategory_name(
            best_subcategory,
            category_config
        )

        index_descriptions = {
            'PERC_INDEX': 'likely to spend',
            'SPC_INDEX': 'spending per customer',
            'SPP_INDEX': 'spending per purchase',
            'PPC_INDEX': 'purchase frequency',
            'COMPOSITE_INDEX': 'overall engagement'
        }

        metric_description = index_descriptions.get(best_index_name, 'engagement')

        if best_index_name == 'PERC_INDEX':
            return (
                f"{self.team_short} fans are {index_diff:.0f}% more likely "
                f"to spend on {subcategory_name} when compared to the NBA average"
            )
        elif best_index_name == 'SPC_INDEX':
            return (
                f"{self.team_short} fans have {index_diff:.0f}% higher spending per customer "
                f"on {subcategory_name} when compared to the NBA average"
            )
        elif best_index_name == 'SPP_INDEX':
            return (
                f"{self.team_short} fans spend {index_diff:.0f}% more per purchase "
                f"on {subcategory_name} when compared to the NBA average"
            )
        elif best_index_name == 'PPC_INDEX':
            return (
                f"{self.team_short} fans make {index_diff:.0f}% more purchases "
                f"of {subcategory_name} when compared to the NBA average"
            )
        else:
            return (
                f"{self.team_short} fans show {index_diff:.0f}% higher overall engagement "
                f"with {subcategory_name} when compared to the NBA average"
            )

    def _get_standardized_name_from_table(self, merchant_name: str, merchant_table: pd.DataFrame) -> str:
        """Get the standardized merchant name from the table"""
        exact_match = merchant_table[merchant_table['Brand'] == merchant_name]
        if not exact_match.empty:
            return merchant_name

        if hasattr(self, 'raw_data') and 'merchant' in self.raw_data:
            merchant_df = self.raw_data['merchant']

            if 'MERCHANT_ORIGINAL' in merchant_df.columns:
                matching_rows = merchant_df[merchant_df['MERCHANT_ORIGINAL'] == merchant_name]
                if not matching_rows.empty:
                    standardized_name = matching_rows.iloc[0]['MERCHANT']
                    return standardized_name

        for _, row in merchant_table.iterrows():
            brand = row['Brand']
            if merchant_name.replace("'", "").replace("-", "").upper() == brand.replace("'", "").replace("-",
                                                                                                         "").upper():
                return brand

        return merchant_name

    def _generate_merchant_insights(self, merchant_stats: Tuple[pd.DataFrame, List[str]],
                                    merchant_df: pd.DataFrame,
                                    merchant_last_year_df: pd.DataFrame = None) -> List[str]:
        """Generate merchant-specific insights with standardized names"""
        merchant_table, top_merchants = merchant_stats
        insights = []

        if merchant_table.empty or not top_merchants:
            return insights

        top_merchant = merchant_table.iloc[0]
        insights.append(
            f"{top_merchant['Percent of Fans Who Spend']} of {self.team_short} fans "
            f"spent at {top_merchant['Brand']}"
        )

        if merchant_last_year_df is not None and not merchant_last_year_df.empty:
            highest_ppc_merchant = self._find_highest_ppc_merchant(merchant_last_year_df, top_merchants)
        else:
            highest_ppc_merchant = self._find_highest_ppc_merchant(merchant_df, top_merchants)

        if highest_ppc_merchant:
            standardized_name = self._get_standardized_name_from_table(
                highest_ppc_merchant['merchant'], merchant_table
            )

            insights.append(
                f"{self.team_name} fans make an average of {highest_ppc_merchant['ppc']:.0f} "
                f"purchases per year at {standardized_name}"
            )

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

            standardized_name = self._get_standardized_name_from_table(
                highest_spc_merchant['merchant'], merchant_table
            )

            insights.append(
                f"{self.team_name} fans spent an average of {formatted_spc} per fan "
                f"on {standardized_name} per year"
            )

        best_nba_merchant = self._find_best_nba_comparison(merchant_df, top_merchants)
        if best_nba_merchant:
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
        """Find merchant with highest purchases per customer"""
        if merchant_df.empty:
            return None

        filtered_df = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['MERCHANT'].isin(top_merchants))
            ]

        if filtered_df.empty:
            return None

        highest_ppc_row = filtered_df.nlargest(1, 'PPC').iloc[0]

        return {
            'merchant': highest_ppc_row['MERCHANT'],
            'ppc': float(highest_ppc_row['PPC'])
        }

    def _find_highest_spc_merchant(self, merchant_df: pd.DataFrame,
                                   top_merchants: List[str]) -> Optional[Dict[str, Any]]:
        """Find merchant with highest spend per customer"""
        if merchant_df.empty:
            return None

        filtered_df = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['MERCHANT'].isin(top_merchants)) &
            (merchant_df['SPC'] > 0)
            ]

        if filtered_df.empty:
            return None

        highest_spc_row = filtered_df.nlargest(1, 'SPC').iloc[0]

        return {
            'merchant': highest_spc_row['MERCHANT'],
            'spc': float(highest_spc_row['SPC'])
        }

    def _find_best_nba_comparison(self, merchant_df: pd.DataFrame,
                                  top_merchants: List[str]) -> Optional[Dict[str, Any]]:
        """Find merchant with best NBA/League comparison"""
        if merchant_df.empty:
            return None

        nba_comp = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['COMPARISON_POPULATION'] == self.league_fans) &
            (merchant_df['MERCHANT'].isin(top_merchants))
            ]

        if nba_comp.empty:
            return None

        best_merchant = nba_comp.nlargest(1, 'PERC_INDEX').iloc[0]
        index_diff = float(best_merchant['PERC_INDEX'])

        if index_diff > self.min_significant_difference:
            return {
                'merchant': best_merchant['MERCHANT'],
                'index_diff': index_diff
            }

        return None

    def _get_sponsorship_recommendation(self, merchant_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate sponsorship recommendation based on composite index"""
        if merchant_df.empty:
            return {}

        team_data = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['COMPARISON_POPULATION'] == self.comparison_pop) &
            (merchant_df['COMPOSITE_INDEX'] > 0) &
            (merchant_df['PERC_AUDIENCE'] >= 0.01)
            ]

        if team_data.empty:
            logger.warning(f"No merchants found with >= 1% audience for {self.team_name}")
            return {
                'merchant': None,
                'composite_index': 0,
                'explanation': f"No brands met the minimum 1% audience threshold for {self.team_short} fans",
                'sub_explanation': "Consider lowering audience requirements or expanding to adjacent categories",
                'full_recommendation': {
                    'main': f"No brands met the minimum 1% audience threshold for {self.team_short} fans",
                    'sub_bullet': "Consider lowering audience requirements or expanding to adjacent categories"
                }
            }

        best_merchant = team_data.nlargest(1, 'COMPOSITE_INDEX').iloc[0]
        merchant_name = best_merchant['MERCHANT']
        composite_index = float(best_merchant['COMPOSITE_INDEX'])
        perc_audience = float(best_merchant['PERC_AUDIENCE'])

        main_recommendation = (
            f"The {self.team_short} should target {merchant_name} for a sponsorship "
            f"based on having the highest composite index of {composite_index:.0f} "
            f"among brands reaching at least 1% of fans ({perc_audience * 100:.1f}% audience)"
        )

        sub_explanation = (
            "The composite index indicates a brand with significant likelihood "
            "for more fans to be spending more frequently, and at a higher spend "
            "per fan vs. other brands"
        )

        return {
            'merchant': merchant_name,
            'composite_index': composite_index,
            'audience_percentage': perc_audience,
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

        for insight in insights:
            if "991%" in insight or any(str(x) + "%" in insight for x in range(900, 1100)):
                issues.append(f"Suspiciously high percentage in insight: {insight}")

            if "NBA" in insight and any(str(x) + "%" in insight for x in range(500, 20000)):
                issues.append(f"Unrealistic NBA comparison: {insight}")

        metric_issues = metrics.validate()
        if metric_issues:
            issues.extend(metric_issues)

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'timestamp': datetime.now().isoformat()
        }

    def _calculate_percent_diff(self, value1: float, value2: float) -> float:
        """Calculate percentage difference"""
        if value2 == 0:
            return 0
        return ((value1 - value2) / value2) * 100

    def _format_subcategory_name(self, subcategory: str, category_config: Dict[str, Any]) -> str:
        """Format subcategory name for display with custom overrides"""
        if subcategory in self.subcategory_overrides:
            return self.subcategory_overrides[subcategory]

        if category_config.get('is_custom', False):
            category_name = category_config.get('display_name', '')
            if subcategory.startswith(f"{category_name} - "):
                return subcategory.replace(f"{category_name} - ", "")
            return subcategory

        if " - " in subcategory:
            return subcategory.split(" - ", 1)[1]

        return subcategory

    def _verify_merchant_threshold(self, category_name: str, merchant_df: pd.DataFrame, threshold: float) -> bool:
        """Check if any merchant in category meets audience threshold"""
        if merchant_df.empty:
            return False

        category_name_clean = category_name.strip()

        category_merchants = merchant_df[
            (merchant_df['AUDIENCE'] == self.audience_name) &
            (merchant_df['CATEGORY'].str.strip() == category_name_clean)
            ]

        if category_merchants.empty:
            logger.debug(f"No merchants found for category '{category_name}'")
            return False

        max_merchant_audience = category_merchants['PERC_AUDIENCE'].max()

        if max_merchant_audience >= threshold:
            top_merchant = category_merchants.loc[category_merchants['PERC_AUDIENCE'].idxmax()]
            logger.info(f"  ✓ Category '{category_name}' has merchant '{top_merchant['MERCHANT']}' "
                        f"with {max_merchant_audience * 100:.1f}% audience")

        return max_merchant_audience >= threshold

    def get_custom_categories(self,
                              category_df: pd.DataFrame,
                              merchant_df: pd.DataFrame,
                              is_womens_team: bool = False,
                              existing_categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get custom categories using tiered selection approach"""
        custom_config = self.config.get('custom_category_config', {})
        team_config = custom_config.get('womens_teams' if is_womens_team else 'mens_teams', {})

        established_config = team_config.get('established_categories', {})
        emerging_config = team_config.get('emerging_category', {})

        established_count = established_config.get('count', 3 if not is_womens_team else 2)
        established_cat_threshold = established_config.get('min_audience_pct', 0.20)
        established_merch_threshold = established_config.get('min_merchant_audience_pct', 0.10)

        emerging_count = emerging_config.get('count', 1 if not is_womens_team else 0)
        emerging_cat_threshold = emerging_config.get('min_audience_pct', 0.10)

        if existing_categories is None:
            existing_fixed = (self.config['fixed_categories']['womens_teams'] if is_womens_team
                              else self.config['fixed_categories']['mens_teams'])
            existing_categories = existing_fixed

        category_names_to_exclude = []
        for cat_key in existing_categories:
            if cat_key in self.categories:
                category_names_to_exclude.extend(
                    self.categories[cat_key].get('category_names_in_data', [])
                )

        base_filter = (
                (category_df['AUDIENCE'] == self.audience_name) &
                (category_df['COMPARISON_POPULATION'] == self.comparison_pop)
        )

        # Find established categories
        established_candidates = category_df[
            base_filter &
            (category_df['PERC_AUDIENCE'] >= established_cat_threshold) &
            (category_df['CATEGORY'].str.strip().isin(self.allowed_custom)) &
            (~category_df['CATEGORY'].str.strip().isin(self.excluded_custom)) &
            (~category_df['CATEGORY'].str.strip().isin(category_names_to_exclude))
            ].copy()

        established_categories = []

        if not established_candidates.empty:
            established_candidates = established_candidates.sort_values('COMPOSITE_INDEX', ascending=False)

            for _, row in established_candidates.iterrows():
                if len(established_categories) >= established_count:
                    break

                category_name = row['CATEGORY']

                if self._verify_merchant_threshold(category_name, merchant_df, established_merch_threshold):
                    category_info = {
                        'category_key': category_name.lower().replace(' ', '_').replace('-', '_'),
                        'display_name': category_name,
                        'category_names_in_data': [category_name],
                        'composite_index': float(row['COMPOSITE_INDEX']),
                        'audience_pct': float(row['PERC_AUDIENCE']),
                        'perc_index': float(row['PERC_INDEX']),
                        'is_custom': True,
                        'is_emerging': False
                    }
                    established_categories.append(category_info)
                    logger.info(f"✓ Selected established category: {category_name}")
                else:
                    logger.info(f"✗ Skipped {category_name} - no merchant meets threshold")

        # Find emerging category
        emerging_categories = []

        if emerging_count > 0 and not is_womens_team:
            selected_category_names = [cat['display_name'] for cat in established_categories]

            emerging_candidates = category_df[
                base_filter &
                (category_df['PERC_AUDIENCE'] >= emerging_cat_threshold) &
                (category_df['CATEGORY'].str.strip().isin(self.allowed_custom)) &
                (~category_df['CATEGORY'].str.strip().isin(self.excluded_custom)) &
                (~category_df['CATEGORY'].str.strip().isin(category_names_to_exclude)) &
                (~category_df['CATEGORY'].isin(selected_category_names))
                ].copy()

            if not emerging_candidates.empty:
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
                    'is_emerging': True
                }
                emerging_categories.append(category_info)
                logger.info(f"★ Selected emerging category: {category_name}")

        all_custom_categories = established_categories + emerging_categories

        logger.info(f"\nCustom category selection complete:")
        logger.info(f"  - Established: {len(established_categories)}")
        logger.info(f"  - Emerging: {len(emerging_categories)}")
        logger.info(f"  - Total: {len(all_custom_categories)}")

        return all_custom_categories

    def create_custom_category_config(self, category_name: str) -> Dict[str, Any]:
        """Create a category configuration for a custom category"""
        category_key = category_name.lower().replace(' ', '_').replace('-', '_')

        if category_key in self.categories:
            predefined_config = self.categories[category_key].copy()
            predefined_config['is_custom'] = True
            logger.info(f"Using predefined config for custom category: {category_name}")
            return predefined_config

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