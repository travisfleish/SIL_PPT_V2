# data_processors/demographic_processor.py
"""
Process demographic data from Snowflake exports to generate insights
for PowerPoint presentations. Handles large datasets (400K+ rows) efficiently.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Union, Optional, Any
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class DemographicsProcessor:
    """Process demographic data for sports team fan analysis"""

    # Expected communities in the data
    EXPECTED_COMMUNITIES = [
        'Utah Jazz Fans',  # Or dynamically set based on team
        'Local Gen Pop (Excl. Jazz)',  # Or 'Local Gen Pop (Excl. {team})'
        'NBA Fans'  # Or '{league} Fans'
    ]

    # Demographic categories expected in the full dataset
    GENERATION_ORDER = [
        '1. Millennials and Gen Z (1982 and after)',
        '2. Generation X (1961-1981)',
        '3. Baby Boomers (1943-1960)',
        '4. Post-WWII (1942 and before)'
    ]

    INCOME_ORDER = [
        'LT_30K',
        '30K_50K',
        '50K_74K',
        '75K_99K',
        '100K_150K',
        'GT_150K'
    ]

    INCOME_LABELS = {
        'LT_30K': '$10,000 to $49,999',  # Combining for display
        '30K_50K': '$10,000 to $49,999',
        '50K_74K': '$50,000 to $74,999',
        '75K_99K': '$75,000 to $99,999',
        '100K_150K': '$100,000 to $149,999',
        'GT_150K': '$150,000 to $199,999'  # Will need to handle $200K+ separately
    }

    OCCUPATION_ORDER = [
        'Blue Collar',
        'Homemaker',
        'Lower Management',
        'Professional',
        'Upper Management',
        'White Collar Worker',
        'Retired',
        'Other'
    ]

    def __init__(self, data_source: Union[str, Path, pd.DataFrame],
                 team_name: str = "Utah Jazz",
                 league: str = "NBA"):
        """
        Initialize the processor with data and team configuration

        Args:
            data_source: Path to data file or DataFrame
            team_name: Name of the team (e.g., "Utah Jazz")
            league: League name (e.g., "NBA")
        """
        self.team_name = team_name
        self.league = league

        # Update expected communities based on team
        self.communities = [
            f'{team_name} Fans',
            f'Local Gen Pop (Excl. {team_name.split()[-1]})',  # Gets last word (Jazz, Cowboys, etc)
            f'{league} Fans'
        ]

        # Load and validate data
        self.data = self._load_data(data_source)
        self._validate_data()

        # Cache for expensive computations
        self._community_totals = None

    def _load_data(self, data_source: Union[str, Path, pd.DataFrame]) -> pd.DataFrame:
        """Load data from file or DataFrame"""
        if isinstance(data_source, pd.DataFrame):
            return data_source.copy()

        # Optimize dtypes for memory efficiency
        dtypes = {
            'CUSTOMER_COUNT': 'int32',
            'CHILDREN_HH': 'int8',
            'NUM_CHILDREN_HH': 'int8',
            'NUM_ADULTS_HH': 'int8'
        }

        file_path = Path(data_source)
        if file_path.suffix == '.csv':
            return pd.read_csv(file_path, dtype=dtypes)
        elif file_path.suffix in ['.xlsx', '.xls']:
            return pd.read_excel(file_path, dtype=dtypes)
        else:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

    def _validate_data(self):
        """Validate that data has required structure"""
        required_columns = [
            'COMMUNITY', 'CUSTOMER_COUNT', 'GENERATION',
            'INCOME_LEVELS', 'OCCUPATION_CATEGORY', 'GENDER',
            'CHILDREN_HH'
        ]

        missing = set(required_columns) - set(self.data.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Check for expected communities
        actual_communities = set(self.data['COMMUNITY'].unique())
        missing_communities = set(self.communities) - actual_communities
        if missing_communities:
            logger.warning(f"Missing communities in data: {missing_communities}")
            # Update communities to what's actually in the data
            self.communities = [c for c in self.communities if c in actual_communities]

        # Log data summary
        total_rows = len(self.data)
        total_customers = self.data['CUSTOMER_COUNT'].sum()
        logger.info(f"Loaded {total_rows:,} rows representing {total_customers:,} customers")

    @lru_cache(maxsize=1)
    def _get_community_totals(self) -> pd.Series:
        """Get total customer counts by community (cached)"""
        return self.data.groupby('COMMUNITY')['CUSTOMER_COUNT'].sum()

    def _calculate_percentages(self, attribute: str,
                               categories: Optional[List[str]] = None) -> Dict[str, Dict[str, float]]:
        """
        Calculate percentage distribution for a demographic attribute

        Args:
            attribute: Column name to analyze
            categories: Optional ordered list of categories

        Returns:
            Dict with structure: {community: {category: percentage}}
        """
        # Group by community and attribute, sum customer counts
        grouped = self.data.groupby(['COMMUNITY', attribute])['CUSTOMER_COUNT'].sum()

        # Get community totals
        community_totals = self._get_community_totals()

        # Calculate percentages
        results = {}
        for community in self.communities:
            if community not in community_totals.index:
                continue

            community_data = grouped[community] if community in grouped else pd.Series()
            total = community_totals[community]

            # Calculate percentages
            percentages = (community_data / total * 100).round(1)

            # If categories provided, ensure all are present
            if categories:
                category_dict = {cat: 0.0 for cat in categories}
                category_dict.update(percentages.to_dict())
                results[community] = category_dict
            else:
                results[community] = percentages.to_dict()

        return results

    def process_generation(self) -> Dict[str, Any]:
        """Process generation/age distribution"""
        percentages = self._calculate_percentages('GENERATION', self.GENERATION_ORDER)

        # Format for charts
        return {
            'chart_type': 'grouped_bar',
            'title': 'Generation',
            'categories': self.GENERATION_ORDER,
            'communities': self.communities,
            'data': percentages,
            'insights': self._generate_generation_insights(percentages)
        }

    def process_income(self) -> Dict[str, Any]:
        """Process household income distribution"""
        raw_percentages = self._calculate_percentages('INCOME_LEVELS', self.INCOME_ORDER)

        # Combine income brackets as shown in PPT
        display_categories = [
            '$10,000 to $49,999',
            '$50,000 to $74,999',
            '$75,000 to $99,999',
            '$100,000 to $149,999',
            '$150,000 to $199,999',
            '$200,000 or more'
        ]

        # Aggregate data for display brackets
        aggregated = {}
        for community, data in raw_percentages.items():
            aggregated[community] = {
                '$10,000 to $49,999': data.get('LT_30K', 0) + data.get('30K_50K', 0),
                '$50,000 to $74,999': data.get('50K_74K', 0),
                '$75,000 to $99,999': data.get('75K_99K', 0),
                '$100,000 to $149,999': data.get('100K_150K', 0),
                '$150,000 to $199,999': data.get('GT_150K', 0) * 0.7,  # Estimate split
                '$200,000 or more': data.get('GT_150K', 0) * 0.3  # Estimate split
            }

        return {
            'chart_type': 'grouped_bar',
            'title': 'Household Income',
            'categories': display_categories,
            'communities': self.communities,
            'data': aggregated,
            'insights': self._generate_income_insights(aggregated)
        }

    def process_occupation(self) -> Dict[str, Any]:
        """Process occupation category distribution"""
        percentages = self._calculate_percentages('OCCUPATION_CATEGORY', self.OCCUPATION_ORDER)

        return {
            'chart_type': 'grouped_bar',
            'title': 'Occupation Category',
            'categories': self.OCCUPATION_ORDER,
            'communities': self.communities,
            'data': percentages,
            'insights': self._generate_occupation_insights(percentages)
        }

    def process_gender(self) -> Dict[str, Any]:
        """Process gender distribution"""
        percentages = self._calculate_percentages('GENDER', ['Male', 'Female'])

        return {
            'chart_type': 'pie',
            'title': 'Gender',
            'categories': ['Male', 'Female'],
            'communities': self.communities,
            'data': percentages,
            'insights': self._generate_gender_insights(percentages)
        }

    def process_children(self) -> Dict[str, Any]:
        """Process children in household distribution"""
        # Create binary categories
        self.data['CHILDREN_CATEGORY'] = self.data['CHILDREN_HH'].apply(
            lambda x: 'At least 1 Child in HH' if x > 0 else 'No Children in HH'
        )

        percentages = self._calculate_percentages(
            'CHILDREN_CATEGORY',
            ['No Children in HH', 'At least 1 Child in HH']
        )

        return {
            'chart_type': 'grouped_bar',
            'title': 'Children in Household',
            'categories': ['No Children in HH', 'At least 1 Child in HH'],
            'communities': self.communities,
            'data': percentages,
            'insights': self._generate_children_insights(percentages)
        }

    def _generate_generation_insights(self, data: Dict) -> List[str]:
        """Generate insights about generation distribution"""
        insights = []

        if self.communities[0] in data and self.communities[1] in data:
            fan_data = data[self.communities[0]]
            gen_pop_data = data[self.communities[1]]

            # Find largest generation for fans
            fan_gen_values = {k: v for k, v in fan_data.items() if v > 0}
            if fan_gen_values:
                top_gen = max(fan_gen_values, key=fan_gen_values.get)
                insights.append(f"{self.team_name} fans are predominantly {top_gen.split('(')[0].strip()}")

            # Compare millennials
            millennial_key = self.GENERATION_ORDER[0]
            if millennial_key in fan_data and millennial_key in gen_pop_data:
                diff = fan_data[millennial_key] - gen_pop_data[millennial_key]
                if diff > 5:
                    insights.append(f"{self.team_name} fans skew younger with {diff:.0f}% more Millennials and Gen Z")

        return insights

    def _generate_income_insights(self, data: Dict) -> List[str]:
        """Generate insights about income distribution"""
        insights = []

        if self.communities[0] in data and self.communities[1] in data:
            fan_data = data[self.communities[0]]
            gen_pop_data = data[self.communities[1]]

            # Calculate high income percentage (>$100K)
            fan_high_income = sum(
                v for k, v in fan_data.items() if '$100,000' in k or '$150,000' in k or '$200,000' in k)
            pop_high_income = sum(
                v for k, v in gen_pop_data.items() if '$100,000' in k or '$150,000' in k or '$200,000' in k)

            if fan_high_income > pop_high_income:
                insights.append(
                    f"{self.team_name} fans are more affluent with {fan_high_income:.0f}% earning over $100K")

        return insights

    def _generate_occupation_insights(self, data: Dict) -> List[str]:
        """Generate insights about occupation distribution"""
        insights = []

        if self.communities[0] in data:
            fan_data = data[self.communities[0]]

            # Find top occupation
            if fan_data:
                top_occupation = max(fan_data, key=fan_data.get)
                insights.append(f"{fan_data[top_occupation]:.0f}% of {self.team_name} fans are {top_occupation}s")

        return insights

    def _generate_gender_insights(self, data: Dict) -> List[str]:
        """Generate insights about gender distribution"""
        # Gender insights might not be highlighted in the main text
        return []

    def _generate_children_insights(self, data: Dict) -> List[str]:
        """Generate insights about children in household"""
        insights = []

        if self.communities[0] in data and self.communities[1] in data:
            fan_data = data[self.communities[0]]
            gen_pop_data = data[self.communities[1]]

            fan_with_children = fan_data.get('At least 1 Child in HH', 0)
            pop_with_children = gen_pop_data.get('At least 1 Child in HH', 0)

            if fan_with_children > pop_with_children + 10:
                insights.append(
                    f"{self.team_name} fans are more likely to be parents ({fan_with_children:.0f}% vs {pop_with_children:.0f}%)")

        return insights

    def process_all_demographics(self) -> Dict[str, Any]:
        """Process all demographic attributes and return complete analysis"""
        logger.info(f"Processing demographics for {self.team_name}")

        results = {
            'team_name': self.team_name,
            'league': self.league,
            'communities': self.communities,
            'total_sample_size': self.data['CUSTOMER_COUNT'].sum(),
            'demographics': {
                'generation': self.process_generation(),
                'income': self.process_income(),
                'occupation': self.process_occupation(),
                'gender': self.process_gender(),
                'children': self.process_children()
            },
            'key_insights': self._generate_summary_insights()
        }

        return results

    def _generate_summary_insights(self) -> str:
        """Generate the main summary text for the demographics slide"""
        all_insights = []

        # Collect insights from each demographic
        demo_results = {
            'generation': self.process_generation(),
            'income': self.process_income(),
            'occupation': self.process_occupation(),
            'children': self.process_children()
        }

        for demo, result in demo_results.items():
            all_insights.extend(result.get('insights', []))

        # Combine insights into a summary
        if all_insights:
            summary_parts = []
            if any('younger' in i for i in all_insights):
                summary_parts.append('younger')
            if any('parent' in i for i in all_insights):
                summary_parts.append('more likely to be parents')
            if any('Professional' in i or 'White Collar' in i for i in all_insights):
                summary_parts.append('who are working professionals')

            if summary_parts:
                return f"{self.team_name} fans are {', and '.join(summary_parts)} versus the {self.team_name.split()[-1]} gen pop."

        return f"{self.team_name} fans have unique demographic characteristics compared to the general population."

    def export_for_visualization(self) -> Dict[str, pd.DataFrame]:
        """Export data in format ready for chart generation"""
        results = self.process_all_demographics()

        # Create DataFrames for each chart
        dataframes = {}

        for demo_type, demo_data in results['demographics'].items():
            if demo_data['chart_type'] == 'grouped_bar':
                # Create DataFrame with communities as columns
                df_data = {}
                for community in self.communities:
                    if community in demo_data['data']:
                        df_data[community] = [
                            demo_data['data'][community].get(cat, 0)
                            for cat in demo_data['categories']
                        ]

                df = pd.DataFrame(df_data, index=demo_data['categories'])
                dataframes[demo_type] = df

            elif demo_data['chart_type'] == 'pie':
                # Create separate DataFrames for each community's pie chart
                for community in self.communities:
                    if community in demo_data['data']:
                        df = pd.DataFrame({
                            'Category': demo_data['categories'],
                            'Percentage': [
                                demo_data['data'][community].get(cat, 0)
                                for cat in demo_data['categories']
                            ]
                        })
                        dataframes[f"{demo_type}_{community}"] = df

        return dataframes


# Example usage
if __name__ == "__main__":
    # Test with sample data
    processor = DemographicsProcessor(
        data_source="data/utah_jazz_demographics.csv",
        team_name="Utah Jazz",
        league="NBA"
    )

    # Process all demographics
    results = processor.process_all_demographics()

    # Print summary
    print(f"Processed {results['total_sample_size']:,} customers")
    print(f"Key insight: {results['key_insights']}")

    # Export for visualization
    chart_data = processor.export_for_visualization()
    print(f"\nGenerated {len(chart_data)} chart datasets")