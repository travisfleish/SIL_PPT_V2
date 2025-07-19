# data_processors/merchant_ranker.py
"""
Merchant Ranker - Fetches top communities and their top merchants from Snowflake
Enhanced with OpenAI-powered merchant name standardization
FIXED VERSION - properly overwrites MERCHANT column with standardized names
"""

import pandas as pd
import yaml
import logging
import asyncio
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MerchantRanker:
    """Analyze and rank merchants by community with merchant name standardization"""

    def __init__(self, team_view_prefix: str = "V_UTAH_JAZZ_SIL"):
        """
        Initialize merchant ranker

        Args:
            team_view_prefix: Snowflake view prefix for the team
        """
        self.team_view_prefix = team_view_prefix
        self.community_view = f"{team_view_prefix}_COMMUNITY_INDEXING_ALL_TIME"
        self.merchant_view = f"{team_view_prefix}_COMMUNITY_MERCHANT_INDEXING_ALL_TIME"

        # Initialize merchant name standardizer
        try:
            from utils.merchant_name_standardizer import MerchantNameStandardizer
            self.standardizer = MerchantNameStandardizer(cache_enabled=True)
            logger.info("✅ Merchant name standardization enabled")
        except ImportError:
            logger.warning("⚠️ MerchantNameStandardizer not available - names will not be standardized")
            self.standardizer = None

        # Load approved communities
        self._load_approved_communities()

    def _load_approved_communities(self):
        """Load approved communities from YAML file"""
        try:
            config_path = Path(__file__).parent.parent / 'config' / 'approved_communities.yaml'
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Create a dict of community name -> action verb
            self.community_actions = {}
            self.approved_communities = set()

            for community in config['approved_communities']:
                name = community['name']
                action = community['action']
                self.approved_communities.add(name)
                self.community_actions[name] = action

            logger.info(f"Loaded {len(self.approved_communities)} approved communities")

        except Exception as e:
            logger.error(f"Error loading approved communities: {e}")
            # Fallback to empty set
            self.approved_communities = set()
            self.community_actions = {}

    def standardize_merchant_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        FIXED VERSION: Standardize merchant names and OVERWRITE the original MERCHANT column

        Args:
            df: DataFrame with 'MERCHANT' column

        Returns:
            DataFrame with standardized merchant names (MERCHANT column is OVERWRITTEN)
        """
        if 'MERCHANT' not in df.columns or df.empty or self.standardizer is None:
            return df

        try:
            logger.info(f"🔄 Standardizing merchant names for {len(df['MERCHANT'].unique())} unique merchants...")

            # Get unique names
            unique_names = df['MERCHANT'].dropna().unique().tolist()

            if not unique_names:
                return df

            # Preserve original names BEFORE overwriting
            df['MERCHANT_ORIGINAL'] = df['MERCHANT'].copy()

            # Get standardized mapping
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                name_mapping = loop.run_until_complete(self.standardizer.standardize_merchants(unique_names))
            finally:
                loop.close()

            # OVERWRITE THE MERCHANT COLUMN (KEY FIX)
            df['MERCHANT'] = df['MERCHANT'].map(name_mapping).fillna(df['MERCHANT'])

            logger.info("✅ Merchant name standardization completed")
            return df

        except Exception as e:
            logger.warning(f"⚠️ Merchant name standardization failed: {e}")
            return df

    def get_top_communities(self,
                            min_audience_pct: float = 0.20,  # Changed from 0.15 to 0.20
                            top_n: int = 10,
                            comparison_pop: str = "Local Gen Pop (Excl. Jazz)") -> pd.DataFrame:
        """
        Get top communities based on composite index

        Args:
            min_audience_pct: Minimum audience percentage threshold (20%)
            top_n: Number of top communities to return
            comparison_pop: Comparison population name

        Returns:
            DataFrame with top communities
        """
        # Build the IN clause for approved communities
        if self.approved_communities:
            communities_list = "', '".join(self.approved_communities)
            community_filter = f"AND COMMUNITY IN ('{communities_list}')"
        else:
            # If no approved communities loaded, use old exclusion logic
            logger.warning("No approved communities loaded, using exclusion logic")
            community_filter = self._get_exclusion_filter()

        query = f"""
        SELECT 
            COMMUNITY,
            PERC_AUDIENCE,
            PERC_INDEX,
            COMPOSITE_INDEX
        FROM 
            {self.community_view}
        WHERE 
            COMPARISON_POPULATION = '{comparison_pop}'
            AND PERC_AUDIENCE >= {min_audience_pct}
            {community_filter}
        ORDER BY COMPOSITE_INDEX DESC
        LIMIT {top_n}
        """

        logger.info(f"Fetching top {top_n} communities from {self.community_view}")
        logger.info(f"Filter: PERC_AUDIENCE >= {min_audience_pct * 100}%")

        # Import here to avoid circular imports
        from data_processors.snowflake_connector import query_to_dataframe

        df = query_to_dataframe(query)
        logger.info(f"Found {len(df)} communities")

        return df

    def _get_exclusion_filter(self):
        """Get the old exclusion filter as fallback"""
        excluded_communities = {
            'General Sports Fans', "Fans of Men's Sports (FOMS)", "Fan's of Men's Sports (FOMS)",
            'NBA', 'Basketball', 'NFL', 'Football', 'American Football', 'College Football',
            'NHL', 'Hockey', 'Ice Hockey', 'MLB', 'Baseball', 'MLS', 'Soccer', 'Football (Soccer)',
            'Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1', 'Champions League',
            'PGA', 'Golf', 'NASCAR', 'Formula 1', 'F1', 'Auto Racing', 'Boxing', 'MMA', 'UFC',
            'Wrestling', 'WWE'
        }

        excluded_patterns = [
            '%NBA%', '%NFL%', '%NHL%', '%MLB%', '%MLS%',
            '%FOOTBALL%', '%BASKETBALL%', '%HOCKEY%', '%BASEBALL%',
            '%SOCCER%', '%GOLF%', '%NASCAR%', '%FORMULA%',
            '%BOXING%', '%UFC%', '%MMA%', '%WRESTLING%'
        ]

        conditions = []
        communities_list = "', '".join(excluded_communities)
        conditions.append(f"AND COMMUNITY NOT IN ('{communities_list}')")

        for pattern in excluded_patterns:
            conditions.append(f"AND UPPER(COMMUNITY) NOT LIKE '{pattern}'")

        return " ".join(conditions)

    def get_top_merchants_for_communities(self,
                                          communities: List[str],
                                          comparison_pop: str = "Local Gen Pop (Excl. Jazz)",
                                          min_audience_count: int = 10,
                                          top_n_per_community: int = 1,
                                          exclude_live_entertainment_sports: bool = True) -> pd.DataFrame:
        """
        Get top merchants for specified communities with standardized names

        Args:
            communities: List of community names
            comparison_pop: Comparison population name
            min_audience_count: Minimum audience count for merchant relevance
            top_n_per_community: Number of top merchants per community
            exclude_live_entertainment_sports: Exclude professional sports from Live Entertainment Seekers

        Returns:
            DataFrame with top merchants for each community (with standardized names)
        """
        # Format communities for SQL
        communities_list = "', '".join(communities)

        # Add exclusion for Live Entertainment Seekers professional sports
        exclusion_clause = ""
        if exclude_live_entertainment_sports:
            exclusion_clause = """
                AND NOT (COMMUNITY = 'Live Entertainment Seekers' 
                        AND LOWER(SUBCATEGORY) LIKE '%professional sports%')
            """

        # Removed COMPOSITE_INDEX since it doesn't exist in merchant view
        query = f"""
        WITH ranked_merchants AS (
            SELECT 
                COMMUNITY,
                MERCHANT,
                CATEGORY,
                SUBCATEGORY,
                PERC_INDEX,
                PERC_AUDIENCE,
                AUDIENCE_TOTAL_SPEND,
                AUDIENCE_COUNT,
                ROW_NUMBER() OVER (PARTITION BY COMMUNITY ORDER BY PERC_AUDIENCE DESC) as rank
            FROM {self.merchant_view}
            WHERE 
                COMMUNITY IN ('{communities_list}')
                AND COMPARISON_POPULATION = '{comparison_pop}'
                AND AUDIENCE_COUNT >= {min_audience_count}
                {exclusion_clause}
        )
        SELECT 
            COMMUNITY,
            MERCHANT,
            CATEGORY,
            SUBCATEGORY,
            PERC_INDEX,
            PERC_AUDIENCE,
            AUDIENCE_TOTAL_SPEND,
            AUDIENCE_COUNT
        FROM ranked_merchants 
        WHERE rank <= {top_n_per_community}
        ORDER BY PERC_AUDIENCE DESC
        """

        logger.info(f"Fetching top merchants for {len(communities)} communities")
        if exclude_live_entertainment_sports:
            logger.info("Excluding professional sports subcategory from Live Entertainment Seekers")
        logger.info("Ranking merchants by PERC_AUDIENCE")

        from data_processors.snowflake_connector import query_to_dataframe

        df = query_to_dataframe(query)
        logger.info(f"Found {len(df)} merchant-community pairs")

        # STANDARDIZE MERCHANT NAMES (MERCHANT column will be overwritten)
        df = self.standardize_merchant_data(df)

        return df

    def get_fan_wheel_data(self,
                           min_audience_pct: float = 0.20,  # Changed from 0.15
                           top_n_communities: int = 10) -> pd.DataFrame:
        """
        Get data formatted for fan wheel visualization with standardized merchant names

        Args:
            min_audience_pct: Minimum audience percentage threshold (20%)
            top_n_communities: Number of communities to include

        Returns:
            DataFrame with one merchant per community for fan wheel (standardized names)
        """
        # Get top communities
        communities_df = self.get_top_communities(
            min_audience_pct=min_audience_pct,
            top_n=top_n_communities
        )

        if communities_df.empty:
            raise ValueError("No communities found matching criteria")

        # Get top merchant for each community (with professional sports excluded)
        communities = communities_df['COMMUNITY'].tolist()
        merchants_df = self.get_top_merchants_for_communities(
            communities=communities,
            top_n_per_community=1,
            exclude_live_entertainment_sports=True  # This is the key change
        )

        # Merge community data with merchant data
        result = merchants_df.merge(
            communities_df[['COMMUNITY', 'PERC_INDEX', 'COMPOSITE_INDEX']].rename(
                columns={
                    'PERC_INDEX': 'COMMUNITY_PERC_INDEX',
                    'COMPOSITE_INDEX': 'COMMUNITY_COMPOSITE_INDEX'
                }
            ),
            on='COMMUNITY',
            how='left'
        )

        # Generate behavior text using approved communities action verbs
        # Now uses standardized merchant names for behavior text
        result['behavior'] = result.apply(
            lambda row: self._generate_behavior_from_community(row['COMMUNITY'], row['MERCHANT']),
            axis=1
        )

        return result

    def _generate_behavior_from_community(self, community: str, merchant: str) -> str:
        """
        Generate behavior text using community action verb from YAML
        Now uses standardized merchant names for better display

        Args:
            community: Community name
            merchant: Merchant name (standardized)

        Returns:
            Behavior text formatted for fan wheel
        """
        # Get action verb from approved communities
        action = self.community_actions.get(community, 'Shops at')

        # Format behavior text
        behavior = f"{action} {merchant}"
        words = behavior.split()

        # Format for two lines for better wheel display
        if len(words) >= 3:
            # Try to split after the action verb
            if len(words) > 3 and len(words[0] + ' ' + words[1]) < 12:
                return f"{words[0]} {words[1]}\n{' '.join(words[2:])}"
            else:
                return f"{words[0]}\n{' '.join(words[1:])}"
        elif len(words) == 2:
            return f"{words[0]}\n{words[1]}"
        else:
            return merchant

    def get_community_index_data(self,
                                 min_audience_pct: float = 0.20,  # Changed from 0.15
                                 top_n: int = 10) -> pd.DataFrame:
        """
        Get community data formatted for index bar chart

        Args:
            min_audience_pct: Minimum audience percentage threshold (20%)
            top_n: Number of communities to include

        Returns:
            DataFrame with community index data for bar chart
        """
        communities_df = self.get_top_communities(
            min_audience_pct=min_audience_pct,
            top_n=top_n
        )

        # Rename columns for chart
        communities_df = communities_df.rename(columns={
            'COMMUNITY': 'Community',
            'PERC_AUDIENCE': 'Audience_Pct',
            'PERC_INDEX': 'Audience_Index'
        })

        # Sort by Audience_Index descending for chart
        communities_df = communities_df.sort_values('Audience_Index', ascending=False)

        return communities_df

    def get_standardized_merchant_ranking(self,
                                          category_filter: str = None,
                                          top_n: int = 10,
                                          comparison_pop: str = "Local Gen Pop (Excl. Jazz)") -> pd.DataFrame:
        """
        Get top merchants with standardized names for any category/analysis

        Args:
            category_filter: Optional category filter (e.g., "Restaurants", "Auto")
            top_n: Number of top merchants to return
            comparison_pop: Comparison population name

        Returns:
            DataFrame with top merchants and standardized names
        """
        # Build category filter
        category_clause = ""
        if category_filter:
            category_clause = f"AND UPPER(CATEGORY) LIKE '%{category_filter.upper()}%'"

        query = f"""
        SELECT 
            MERCHANT,
            CATEGORY,
            SUBCATEGORY,
            PERC_INDEX,
            PERC_AUDIENCE,
            AUDIENCE_TOTAL_SPEND,
            AUDIENCE_COUNT
        FROM {self.merchant_view}
        WHERE 
            COMPARISON_POPULATION = '{comparison_pop}'
            {category_clause}
        ORDER BY PERC_AUDIENCE DESC
        LIMIT {top_n}
        """

        from data_processors.snowflake_connector import query_to_dataframe
        df = query_to_dataframe(query)

        # STANDARDIZE MERCHANT NAMES (MERCHANT column will be overwritten)
        df = self.standardize_merchant_data(df)

        return df


# Example usage
if __name__ == "__main__":
    # Test the enhanced merchant ranker
    print("🧪 Testing Fixed MerchantRanker with Name Standardization")
    print("=" * 60)

    ranker = MerchantRanker()

    # Test 1: Get fan wheel data (with standardized names)
    print("\n📊 Testing Fan Wheel Data...")
    try:
        wheel_data = ranker.get_fan_wheel_data()
        print("✅ Fan Wheel Data (with standardized names):")
        print("Note: MERCHANT column should now show standardized names!")

        display_cols = ['COMMUNITY', 'MERCHANT', 'behavior', 'PERC_AUDIENCE', 'PERC_INDEX']
        if 'MERCHANT_ORIGINAL' in wheel_data.columns:
            display_cols.insert(2, 'MERCHANT_ORIGINAL')

        print(wheel_data[display_cols].head())

        # Show comparison if original column exists
        if 'MERCHANT_ORIGINAL' in wheel_data.columns:
            print("\n🎯 Name Standardization Comparison:")
            print("-" * 60)
            for _, row in wheel_data.head(5).iterrows():
                original = row['MERCHANT_ORIGINAL']
                standardized = row['MERCHANT']
                changed = "🔄" if original != standardized else "   "
                print(f"   {original} → {standardized} {changed}")

    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: Get standardized merchant ranking
    print("\n🏪 Testing Standardized Merchant Ranking...")
    try:
        merchant_ranking = ranker.get_standardized_merchant_ranking(
            category_filter="Restaurants",
            top_n=5
        )
        print("✅ Top 5 Restaurant Merchants (standardized):")

        if 'MERCHANT_ORIGINAL' in merchant_ranking.columns:
            print("Original vs Standardized:")
            for _, row in merchant_ranking.iterrows():
                orig = row['MERCHANT_ORIGINAL']
                std = row['MERCHANT']
                changed = "🔄" if orig != std else "   "
                print(f"   {orig} → {std} {changed}")
        else:
            print(merchant_ranking[['MERCHANT', 'PERC_AUDIENCE']].to_string(index=False))

    except Exception as e:
        print(f"❌ Error: {e}")

    print(f"\n✅ Testing completed!")
    print("\n📝 Key Changes:")
    print("   ✅ MERCHANT column is now OVERWRITTEN with standardized names")
    print("   ✅ Original names preserved in MERCHANT_ORIGINAL column")
    print("   ✅ Fan wheel behavior text uses standardized names")
    print("   ✅ All display logic sees standardized names in MERCHANT column")