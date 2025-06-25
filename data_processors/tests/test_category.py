# test_merchant_insights_real.py
"""
Test script for revised merchant insights generation using real Snowflake data
Validates the data-driven selection logic for brand insights
"""

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import json

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_processors.category_analyzer import CategoryAnalyzer
from data_processors.snowflake_connector import query_to_dataframe, test_connection
from utils.team_config_manager import TeamConfigManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_merchant_metrics(merchant_df: pd.DataFrame, analyzer: CategoryAnalyzer) -> dict:
    """
    Analyze merchant data to identify which merchants should win each metric

    Returns:
        Dictionary with expected winners for each metric
    """
    # Filter for team fans
    team_data = merchant_df[merchant_df['AUDIENCE'] == analyzer.audience_name]

    if team_data.empty:
        return {}

    # Get top 5 merchants by audience percentage
    top_5_merchants = (team_data
                       .sort_values('PERC_AUDIENCE', ascending=False)
                       .drop_duplicates('MERCHANT')
                       .head(5)['MERCHANT'].tolist())

    # Initialize tracking variables
    metrics_analysis = {
        'top_by_audience': {'merchant': None, 'value': 0},
        'highest_ppc': {'merchant': None, 'value': 0},
        'highest_spc': {'merchant': None, 'value': 0},
        'highest_composite': {'merchant': None, 'value': 0},
        'best_nba_index': {'merchant': None, 'value': 0, 'diff': 0}
    }

    # Analyze each top 5 merchant
    for i, merchant in enumerate(top_5_merchants):
        # Get data for this merchant
        m_data = team_data[team_data['MERCHANT'] == merchant].iloc[0]

        # Track top by audience (should be first merchant)
        if i == 0:
            metrics_analysis['top_by_audience'] = {
                'merchant': merchant,
                'value': float(m_data['PERC_AUDIENCE']) * 100
            }

        # Check PPC
        ppc_value = float(m_data.get('PPC', 0))
        if ppc_value > metrics_analysis['highest_ppc']['value']:
            metrics_analysis['highest_ppc'] = {
                'merchant': merchant,
                'value': ppc_value
            }

        # Check SPC
        spc_value = float(m_data.get('SPC', 0))
        if spc_value > metrics_analysis['highest_spc']['value']:
            metrics_analysis['highest_spc'] = {
                'merchant': merchant,
                'value': spc_value
            }

        # Check Composite Index
        composite_value = float(m_data.get('COMPOSITE_INDEX', 0))
        if composite_value > metrics_analysis['highest_composite']['value']:
            metrics_analysis['highest_composite'] = {
                'merchant': merchant,
                'value': composite_value
            }

        # Check NBA/League comparison
        nba_data = merchant_df[
            (merchant_df['MERCHANT'] == merchant) &
            (merchant_df['AUDIENCE'] == analyzer.audience_name) &
            (merchant_df['COMPARISON_POPULATION'] == analyzer.league_fans)
            ]

        if not nba_data.empty:
            perc_index = float(nba_data.iloc[0].get('PERC_INDEX', 100))
            index_diff = perc_index - 100

            if index_diff > metrics_analysis['best_nba_index']['diff']:
                metrics_analysis['best_nba_index'] = {
                    'merchant': merchant,
                    'value': perc_index,
                    'diff': index_diff
                }

    return metrics_analysis


def test_category_merchants(team_key: str = 'utah_jazz', category_key: str = 'auto'):
    """
    Test merchant insights for a specific team and category

    Args:
        team_key: Team identifier
        category_key: Category to test
    """
    print(f"\n{'=' * 80}")
    print(f"TESTING MERCHANT INSIGHTS: {team_key} - {category_key}")
    print(f"{'=' * 80}")

    # Test connection
    print("\n1. Testing Snowflake connection...")
    if not test_connection():
        print("❌ Failed to connect to Snowflake")
        return None
    print("✅ Connected to Snowflake")

    # Get team configuration
    print("\n2. Loading team configuration...")
    config_manager = TeamConfigManager()
    team_config = config_manager.get_team_config(team_key)
    view_prefix = team_config['view_prefix']
    print(f"✅ Team: {team_config['team_name']}")
    print(f"   View prefix: {view_prefix}")

    # Initialize analyzer
    print("\n3. Initializing CategoryAnalyzer...")
    analyzer = CategoryAnalyzer(
        team_name=team_config['team_name'],
        team_short=team_config['team_name_short'],
        league=team_config['league']
    )

    # Get category configuration
    category_config = analyzer.categories.get(category_key)
    if not category_config:
        print(f"❌ Unknown category: {category_key}")
        return None

    # Build category filter
    category_names = category_config.get('category_names_in_data', [])
    category_list = ','.join([f"'{c}'" for c in category_names])
    category_where = f"CATEGORY IN ({category_list})"

    # Load merchant data
    print(f"\n4. Loading merchant data for {category_config['display_name']}...")
    merchant_query = f"""
    SELECT * FROM {view_prefix}_MERCHANT_INDEXING_ALL_TIME 
    WHERE {category_where}
    ORDER BY AUDIENCE, MERCHANT, COMPARISON_POPULATION
    """

    try:
        merchant_df = query_to_dataframe(merchant_query)
        print(f"✅ Loaded {len(merchant_df)} merchant records")
    except Exception as e:
        print(f"❌ Failed to load merchant data: {str(e)}")
        return None

    # Create minimal dataframes for other required data
    category_df = pd.DataFrame()
    subcategory_df = pd.DataFrame()

    # Analyze expected metrics
    print("\n5. Analyzing merchant metrics...")
    expected_metrics = analyze_merchant_metrics(merchant_df, analyzer)

    if expected_metrics:
        print("\nExpected Winners by Metric:")
        print("-" * 60)
        print(f"Top by Audience %: {expected_metrics['top_by_audience']['merchant']} "
              f"({expected_metrics['top_by_audience']['value']:.1f}%)")
        print(f"Highest PPC: {expected_metrics['highest_ppc']['merchant']} "
              f"({expected_metrics['highest_ppc']['value']:.1f} purchases)")
        print(f"Highest SPC: {expected_metrics['highest_spc']['merchant']} "
              f"(${expected_metrics['highest_spc']['value']:.2f})")
        print(f"Best {analyzer.league} Index: {expected_metrics['best_nba_index']['merchant']} "
              f"({expected_metrics['best_nba_index']['diff']:.0f}% more likely)")
        print(f"Highest Composite: {expected_metrics['highest_composite']['merchant']} "
              f"({expected_metrics['highest_composite']['value']:.0f})")

    # Run the analysis
    print("\n6. Running category analysis...")
    try:
        results = analyzer.analyze_category(
            category_key=category_key,
            category_df=category_df,
            subcategory_df=subcategory_df,
            merchant_df=merchant_df,
            validate=False
        )
        print("✅ Analysis completed successfully")
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

    # Display and validate results
    print(f"\n{'=' * 60}")
    print("GENERATED MERCHANT INSIGHTS:")
    print(f"{'=' * 60}")

    validation_results = []

    for i, insight in enumerate(results['merchant_insights'], 1):
        print(f"\nInsight {i}: {insight}")

        # Validate each insight
        validation = {'insight_num': i, 'text': insight, 'valid': False, 'issue': None}

        if i == 1:
            # Should show top merchant by audience
            expected = expected_metrics['top_by_audience']['merchant']
            expected_pct = f"{expected_metrics['top_by_audience']['value']:.0f}%"
            if expected in insight and expected_pct in insight:
                print(f"   ✅ Correct: Shows {expected} with {expected_pct}")
                validation['valid'] = True
            else:
                print(f"   ❌ Expected: {expected} with {expected_pct}")
                validation['issue'] = f"Expected {expected} with {expected_pct}"

        elif i == 2:
            # Should show highest PPC merchant
            expected = expected_metrics['highest_ppc']['merchant']
            expected_ppc = int(expected_metrics['highest_ppc']['value'])
            if expected in insight and (
                    f"{expected_ppc} purchases" in insight or
                    f"{expected_ppc} purchase" in insight
            ):
                print(f"   ✅ Correct: Shows {expected} with highest PPC")
                validation['valid'] = True
            else:
                print(f"   ❌ Expected: {expected} with {expected_ppc} purchases")
                validation['issue'] = f"Expected {expected} with {expected_ppc} purchases"

        elif i == 3:
            # Should show highest SPC merchant
            expected = expected_metrics['highest_spc']['merchant']
            expected_spc = expected_metrics['highest_spc']['value']
            if expected in insight and f"${expected_spc:.2f}" in insight:
                print(f"   ✅ Correct: Shows {expected} with highest SPC")
                validation['valid'] = True
            else:
                print(f"   ❌ Expected: {expected} with ${expected_spc:.2f}")
                validation['issue'] = f"Expected {expected} with ${expected_spc:.2f}"

        elif i == 4:
            # Should show best NBA/League comparison
            expected = expected_metrics['best_nba_index']['merchant']
            expected_diff = int(expected_metrics['best_nba_index']['diff'])
            if expected in insight and f"{expected_diff}% more likely" in insight:
                print(f"   ✅ Correct: Shows {expected} with best league comparison")
                validation['valid'] = True
            else:
                print(f"   ❌ Expected: {expected} {expected_diff}% more likely")
                validation['issue'] = f"Expected {expected} {expected_diff}% more likely"

        validation_results.append(validation)

    # Check sponsorship recommendation
    print(f"\n{'=' * 60}")
    print("SPONSORSHIP RECOMMENDATION:")
    print(f"{'=' * 60}")

    rec = results.get('recommendation')
    rec_validation = {'valid': False, 'issue': None}

    if rec:
        print(f"\nTarget: {rec['merchant']}")
        print(f"Composite Index: {rec['composite_index']:.0f}")
        print(f"\nMain: {rec['explanation']}")
        print(f"Sub-bullet: {rec['sub_explanation']}")

        # Validate recommendation
        expected_merchant = expected_metrics['highest_composite']['merchant']
        expected_index = expected_metrics['highest_composite']['value']

        if (rec['merchant'] == expected_merchant and
                abs(rec['composite_index'] - expected_index) < 1):
            print(f"\n✅ Correct: Recommends {expected_merchant} with highest composite index")
            rec_validation['valid'] = True
        else:
            print(f"\n❌ Expected: {expected_merchant} with index {expected_index:.0f}")
            rec_validation['issue'] = f"Expected {expected_merchant} with index {expected_index:.0f}"
    else:
        print("\n❌ No recommendation generated")
        rec_validation['issue'] = "No recommendation generated"

    # Summary
    print(f"\n{'=' * 60}")
    print("VALIDATION SUMMARY:")
    print(f"{'=' * 60}")

    valid_insights = sum(1 for v in validation_results if v['valid'])
    total_insights = len(validation_results)

    print(f"\nInsights: {valid_insights}/{total_insights} valid")
    print(f"Recommendation: {'✅ Valid' if rec_validation['valid'] else '❌ Invalid'}")

    if valid_insights == total_insights and rec_validation['valid']:
        print(f"\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n❌ Some tests failed - review issues above")

    return {
        'team': team_key,
        'category': category_key,
        'validation_results': validation_results,
        'recommendation_validation': rec_validation,
        'expected_metrics': expected_metrics,
        'generated_insights': results.get('merchant_insights', []),
        'generated_recommendation': rec
    }


def test_multiple_categories(team_key: str = 'utah_jazz'):
    """Test multiple categories for a team"""
    print(f"\n{'=' * 80}")
    print(f"COMPREHENSIVE TEST: {team_key}")
    print(f"{'=' * 80}")

    # Test fixed categories
    test_categories = ['restaurants', 'auto', 'athleisure', 'finance']
    all_results = {}

    for category in test_categories:
        results = test_category_merchants(team_key, category)
        if results:
            all_results[category] = results

    # Summary report
    print(f"\n{'=' * 80}")
    print("OVERALL TEST SUMMARY:")
    print(f"{'=' * 80}")

    for category, results in all_results.items():
        valid_insights = sum(1 for v in results['validation_results'] if v['valid'])
        total_insights = len(results['validation_results'])
        rec_valid = results['recommendation_validation']['valid']

        status = "✅ PASS" if valid_insights == total_insights and rec_valid else "❌ FAIL"
        print(f"\n{category.upper()}: {status}")
        print(f"  - Insights: {valid_insights}/{total_insights} valid")
        print(f"  - Recommendation: {'Valid' if rec_valid else 'Invalid'}")

    # Save detailed results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"merchant_insights_test_{team_key}_{timestamp}.json"

    # Convert results to serializable format
    serializable_results = {}
    for category, results in all_results.items():
        serializable_results[category] = {
            'validation_summary': {
                'insights_valid': sum(1 for v in results['validation_results'] if v['valid']),
                'insights_total': len(results['validation_results']),
                'recommendation_valid': results['recommendation_validation']['valid']
            },
            'expected_winners': {
                metric: {
                    'merchant': data['merchant'],
                    'value': float(data['value']) if data['merchant'] else None
                }
                for metric, data in results['expected_metrics'].items()
            },
            'generated_insights': results['generated_insights'],
            'issues': [
                v['issue'] for v in results['validation_results']
                if not v['valid'] and v['issue']
            ]
        }

    with open(output_file, 'w') as f:
        json.dump(serializable_results, f, indent=2)

    print(f"\n📄 Detailed results saved to: {output_file}")


def main():
    """Main test function"""
    print("\n🧪 MERCHANT INSIGHTS VALIDATION TEST")
    print("Testing data-driven merchant selection logic")
    print("=" * 80)

    # Test single category
    test_category_merchants('utah_jazz', 'auto')

    # Test multiple categories
    # test_multiple_categories('utah_jazz')

    # Test other teams if available
    # test_category_merchants('dallas_cowboys', 'restaurants')


if __name__ == "__main__":
    main()