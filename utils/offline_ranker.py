import pandas as pd
from pathlib import Path
from typing import Optional, List
import logging
import yaml

logger = logging.getLogger(__name__)


class OfflineMerchantRanker:
    """
    Minimal drop-in replacement for MerchantRanker that reads pre-exported CSVs.
    Exposes get_top_communities() and get_fan_wheel_data() used by behaviors slide.
    """

    def __init__(
        self,
        community_csv: Path,
        community_merchant_csv: Path,
        comparison_population: str,
        audience_name: str,
    ):
        self.comparison_population = comparison_population
        self.audience_name = audience_name

        self.community_df = pd.read_csv(community_csv)
        self.community_merchant_df = pd.read_csv(community_merchant_csv)

        # Basic normalization
        for df in [self.community_df, self.community_merchant_df]:
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].astype(str).str.strip()

        # Ensure numeric columns are numeric
        for col in ['PERC_AUDIENCE', 'PERC_INDEX', 'COMPOSITE_INDEX']:
            for df in [self.community_df, self.community_merchant_df]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

        # Load approved communities (same as MerchantRanker)
        self._load_approved_communities()

        # Merchant exclusions (same as MerchantRanker)
        self.EXCLUDED_MERCHANTS = ['LEVELUP']
        # Custom runtime merchant exclusions (standardized names)
        self.custom_excluded_merchants = set()

    def set_custom_excluded_merchants(self, names: List[str]):
        """Set additional merchants to exclude (case-insensitive, after standardization)."""
        self.custom_excluded_merchants = {n.upper() for n in names or []}

    def _load_approved_communities(self):
        """Load approved communities and action verbs from YAML (same file used by MerchantRanker)."""
        try:
            config_path = Path(__file__).parent.parent / 'config' / 'approved_communities.yaml'
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            self.community_actions = {}
            self.approved_communities = set()

            for community in config.get('approved_communities', []):
                name = community['name']
                action = community['action']
                self.approved_communities.add(name)
                self.community_actions[name] = action

            logger.info(f"Loaded {len(self.approved_communities)} approved communities (offline)")
        except Exception as e:
            logger.warning(f"Could not load approved_communities.yaml (offline): {e}")
            self.approved_communities = set()
            self.community_actions = {}

    def _apply_community_exclusions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply same exclusion logic as MerchantRanker when no approved list is available."""
        excluded_communities = {
            'General Sports Fans', "Fans of Men's Sports (FOMS)", "Fan's of Men's Sports (FOMS)",
            'NBA', 'Basketball', 'NFL', 'Football', 'American Football', 'College Football',
            'NHL', 'Hockey', 'Ice Hockey', 'MLB', 'Baseball', 'MLS', 'Soccer', 'Football (Soccer)',
            'Premier League', 'La Liga', 'Bundesliga', 'Serie A', 'Ligue 1', 'Champions League',
            'PGA', 'Golf', 'NASCAR', 'Formula 1', 'F1', 'Auto Racing', 'Boxing', 'MMA', 'UFC',
            'Wrestling', 'WWE'
        }

        excluded_patterns = [
            'NBA', 'NFL', 'NHL', 'MLB', 'MLS',
            'FOOTBALL', 'BASKETBALL', 'HOCKEY', 'BASEBALL',
            'SOCCER', 'GOLF', 'NASCAR', 'FORMULA',
            'BOXING', 'UFC', 'MMA', 'WRESTLING'
        ]

        # Exclude exact community names
        if 'COMMUNITY' not in df.columns:
            return df
        mask = ~df['COMMUNITY'].isin(excluded_communities)

        # Exclude pattern matches (case-insensitive substring)
        upper = df['COMMUNITY'].str.upper()
        for pat in excluded_patterns:
            mask &= ~upper.str.contains(pat, na=False)

        return df[mask]

    def get_community_metrics_for(self, communities: List[str]) -> pd.DataFrame:
        """Return STM/GP metrics for a provided ordered community list.

        Returns DataFrame with columns: COMMUNITY, PERC_AUDIENCE, COMPOSITE_INDEX
        in the same order as the input list (skipping those not found).
        """
        if not communities:
            return pd.DataFrame(columns=['COMMUNITY', 'PERC_AUDIENCE', 'COMPOSITE_INDEX'])

        df = self.community_df[
            (self.community_df.get('AUDIENCE', '') == self.audience_name)
            & (self.community_df.get('COMPARISON_POPULATION', '') == self.comparison_population)
            & (self.community_df['COMMUNITY'].isin(communities))
        ].copy()

        if df.empty:
            return pd.DataFrame(columns=['COMMUNITY', 'PERC_AUDIENCE', 'COMPOSITE_INDEX'])

        # Reduce duplicates by taking the highest COMPOSITE_INDEX per community
        if 'COMPOSITE_INDEX' in df.columns:
            df = df.sort_values('COMPOSITE_INDEX', ascending=False).drop_duplicates('COMMUNITY', keep='first')
        elif 'PERC_INDEX' in df.columns:
            df = df.sort_values('PERC_INDEX', ascending=False).drop_duplicates('COMMUNITY', keep='first')
        else:
            df = df.sort_values('PERC_AUDIENCE', ascending=False).drop_duplicates('COMMUNITY', keep='first')

        # Preserve the requested order
        order = {c: i for i, c in enumerate(communities)}
        df['__order'] = df['COMMUNITY'].map(order)
        df = df.sort_values('__order').drop(columns='__order')

        return df[['COMMUNITY', 'PERC_AUDIENCE', 'COMPOSITE_INDEX'] if 'COMPOSITE_INDEX' in df.columns else ['COMMUNITY', 'PERC_AUDIENCE']]

    def get_top_communities(self, min_audience_pct: float = 0.20, top_n: int = 10):
        df = self.community_df

        # Expect columns: COMMUNITY, PERC_AUDIENCE, PERC_INDEX, COMPOSITE_INDEX, COMPARISON_POPULATION
        filtered = df[
            (df.get('AUDIENCE', '') == self.audience_name)
            & (df.get('COMPARISON_POPULATION', '') == self.comparison_population)
            & (df.get('PERC_AUDIENCE', 0) >= min_audience_pct)
        ].copy()

        # Apply approved communities if available, else apply exclusion logic
        if self.approved_communities:
            filtered = filtered[filtered['COMMUNITY'].isin(self.approved_communities)]
        else:
            filtered = self._apply_community_exclusions(filtered)

        if 'COMPOSITE_INDEX' not in filtered.columns:
            # If not provided, fallback to sorting by PERC_INDEX
            sort_col = 'PERC_INDEX' if 'PERC_INDEX' in filtered.columns else 'PERC_AUDIENCE'
        else:
            sort_col = 'COMPOSITE_INDEX'

        result = filtered.sort_values(sort_col, ascending=False).head(top_n)

        # Fallback: if fewer than requested, relax threshold and pad with next best
        if len(result) < top_n:
            # Recompute without the audience threshold but same audience/comparison and exclusions
            fallback = self.community_df[
                (self.community_df.get('AUDIENCE', '') == self.audience_name)
                & (self.community_df.get('COMPARISON_POPULATION', '') == self.comparison_population)
            ].copy()

            if self.approved_communities:
                fallback = fallback[fallback['COMMUNITY'].isin(self.approved_communities)]
            else:
                fallback = self._apply_community_exclusions(fallback)

            if 'COMPOSITE_INDEX' not in fallback.columns:
                fb_sort = 'PERC_INDEX' if 'PERC_INDEX' in fallback.columns else 'PERC_AUDIENCE'
            else:
                fb_sort = 'COMPOSITE_INDEX'

            fallback = fallback.sort_values(fb_sort, ascending=False)

            # Append communities not already selected until we reach top_n
            have = set(result['COMMUNITY'].tolist())
            to_add = []
            for _, row in fallback.iterrows():
                if row['COMMUNITY'] not in have:
                    to_add.append(row)
                if len(result) + len(to_add) >= top_n:
                    break
            if to_add:
                import pandas as pd
                result = pd.concat([result, pd.DataFrame(to_add)], ignore_index=True).head(top_n)

        return result

    def get_top_merchants_for_communities(
        self,
        communities: List[str],
        min_audience_count: int = 10,
        top_n_per_community: int = 1,
        exclude_live_entertainment_sports: bool = True,
    ) -> pd.DataFrame:
        """Offline equivalent of MerchantRanker.get_top_merchants_for_communities."""
        df = self.community_merchant_df

        # Base filters
        filtered = df[
            (df.get('COMPARISON_POPULATION', '') == self.comparison_population)
            & (df.get('AUDIENCE', '') == self.audience_name)
            & (df['COMMUNITY'].isin(communities))
        ].copy()

        # Exclude live entertainment professional sports if requested
        if exclude_live_entertainment_sports and 'SUBCATEGORY' in filtered.columns:
            mask = ~(
                (filtered['COMMUNITY'] == 'Live Entertainment Seekers')
                & (filtered['SUBCATEGORY'].str.lower().str.contains('professional sports', na=False))
            )
            filtered = filtered[mask]

        # Exclude specific merchants
        if self.EXCLUDED_MERCHANTS and 'MERCHANT' in filtered.columns:
            excluded_upper = [m.upper() for m in self.EXCLUDED_MERCHANTS]
            filtered = filtered[~filtered['MERCHANT'].str.upper().isin(excluded_upper)]
        # Apply custom exclusions if any
        if self.custom_excluded_merchants and 'MERCHANT' in filtered.columns:
            filtered = filtered[~filtered['MERCHANT'].str.upper().isin(self.custom_excluded_merchants)]

        # Note: For offline one-off runs, do not enforce a minimum AUDIENCE_COUNT

        # Rank within each community by PERC_AUDIENCE
        filtered = filtered.sort_values(['COMMUNITY', 'PERC_AUDIENCE'], ascending=[True, False])
        result = filtered.groupby('COMMUNITY', as_index=False).head(top_n_per_community)

        return result

    def _generate_behavior_from_community(self, community: str, merchant: str) -> str:
        action = self.community_actions.get(community, 'Shops at')
        words = (action + ' ' + merchant).split()
        if len(words) >= 3:
            if len(words) > 3 and len(words[0] + ' ' + words[1]) < 12:
                return f"{words[0]} {words[1]}\n{' '.join(words[2:])}"
            return f"{words[0]}\n{' '.join(words[1:])}"
        if len(words) == 2:
            return f"{words[0]}\n{words[1]}"
        return merchant

    def get_fan_wheel_data(
        self,
        min_audience_pct: float = 0.20,
        top_n_communities: int = 10,
    ):
        # Top communities with same inclusion/exclusion logic
        # Expand candidate pool and take UNIQUE community names in order
        candidate_n = max(top_n_communities * 50, 50)
        top_comms_full = self.get_top_communities(
            min_audience_pct=min_audience_pct, top_n=candidate_n
        )

        unique_comms = []
        for c in top_comms_full['COMMUNITY'].tolist():
            if c not in unique_comms:
                unique_comms.append(c)
            if len(unique_comms) >= top_n_communities:
                break

        # Fallback: if still not enough (extreme duplication), drop threshold
        if len(unique_comms) < top_n_communities:
            extra_pool = self.get_top_communities(min_audience_pct=0.0, top_n=candidate_n)
            for c in extra_pool['COMMUNITY'].tolist():
                if c not in unique_comms:
                    unique_comms.append(c)
                if len(unique_comms) >= top_n_communities:
                    break

        communities = unique_comms

        # Fetch top N merchants per community (use >1 to allow greedy unique selection)
        merchants_all = self.get_top_merchants_for_communities(
            communities=communities,
            min_audience_count=10,
            top_n_per_community=5,
            exclude_live_entertainment_sports=True,
        )

        # Standardize merchant names BEFORE greedy selection to avoid duplicates due to casing
        try:
            from utils.merchant_name_standardizer import MerchantNameStandardizer
            standardizer = MerchantNameStandardizer(cache_enabled=True, cache_manager=self.__dict__.get('cache_manager'))
            unique_names = merchants_all['MERCHANT'].dropna().unique().tolist()
            if unique_names:
                mapping = standardizer.standardize_merchants_sync(unique_names) if hasattr(standardizer,'standardize_merchants_sync') else None
                if mapping is None:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        mapping = loop.run_until_complete(standardizer.standardize_merchants(unique_names))
                    finally:
                        loop.close()
                if mapping:
                    merchants_all['MERCHANT'] = merchants_all['MERCHANT'].map(mapping).fillna(merchants_all['MERCHANT'])
        except Exception:
            pass

        # Greedy selection: one unique merchant per community, preserving community order
        selected_rows = []
        used_merchants = set()
        # Keep order by community list
        merchants_all['__rank'] = merchants_all['COMMUNITY'].apply(lambda c: communities.index(c) if c in communities else 999)
        merchants_all = merchants_all.sort_values(['__rank', 'PERC_AUDIENCE'], ascending=[True, False])

        for community in communities:
            pool = merchants_all[merchants_all['COMMUNITY'] == community]
            chosen = None
            for _, row in pool.iterrows():
                merchant = row['MERCHANT']
                if merchant not in used_merchants:
                    chosen = row
                    used_merchants.add(merchant)
                    break
            if chosen is None and not pool.empty:
                chosen = pool.iloc[0]
                used_merchants.add(chosen['MERCHANT'])
            if chosen is not None:
                selected_rows.append(chosen)

        result = pd.DataFrame(selected_rows)

        # Behavior text using approved community actions
        result['behavior'] = result.apply(
            lambda r: self._generate_behavior_from_community(r['COMMUNITY'], r['MERCHANT']), axis=1
        )

        needed_cols = ['COMMUNITY', 'MERCHANT', 'behavior', 'PERC_INDEX']
        for col in needed_cols:
            if col not in result.columns:
                result[col] = '' if col in ['COMMUNITY', 'MERCHANT', 'behavior'] else 0

        return result[needed_cols]


