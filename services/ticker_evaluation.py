import yfinance as yf
from yahoo_fin import stock_info as si
import yfinance as yf
from typing import Dict, Tuple, Optional
import pandas as pd
import json

def find_ticker(company_name):
    """
    Find the ticker symbol for a given company name.

    Args:
        company_name (str): The name of the company

    Returns:
        list: List of tuples containing (ticker, full_name)
    """
    try:
        # Common suffixes to try removing
        suffixes = [' Inc', ' Inc.', ' Corporation', ' Corp', ' Corp.',
                   ' Ltd', ' Ltd.', ' Limited', ' LLC', ' Co', ' Co.']

        # Load companies data from JSON file
        with open('companies_data.json', 'r') as f:
            companies_data = json.load(f)
            common_companies = {k: v for category in companies_data.values() 
                              for k, v in category.items()}

        # Check if it's a well-known company first
        company_check = company_name.lower().strip()
        if company_check in common_companies:
            ticker = common_companies[company_check]
            stock = yf.Ticker(ticker)
            info = stock.info
            return [(ticker, info.get('longName', company_name))]


        # Try to find the company
        results = []

        # Clean the company name
        clean_name = company_name.strip()
        for suffix in suffixes:
            clean_name = clean_name.replace(suffix, '')

        try:
            # Get list of tickers that match the search
            tickers = si.tickers_dow() + si.tickers_nasdaq() + si.tickers_sp500()

            # Filter tickers based on company name
            potential_matches = []
            for ticker in tickers:
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    company_info = info.get('longName', '').lower()

                    if (clean_name.lower() in company_info or
                        company_info in clean_name.lower()):
                        potential_matches.append((ticker, info.get('longName', '')))
                except:
                    continue

            if potential_matches:
                return potential_matches

        except Exception as e:
            print(f"Error in ticker search: {e}")

        return results

    except Exception as e:
        return [("Error", str(e))]

def print_ticker_results(results):
    """
    Print the ticker search results in a formatted way.

    Args:
        results (list): List of (ticker, name) tuples
    """
    if not results:
        print("No results found.")
        return

    if results[0][0] == "Error":
        print(f"Error occurred: {results[0][1]}")
        return

    print("\nFound the following matches:")
    print("-" * 70)
    print(f"{'Ticker':<10} {'Company Name':<60}")
    print("-" * 70)

    for ticker, name in results:
        print(f"{ticker:<10} {name[:60]:<60}")


def analyze_merger_eumr_compliance(company1_ticker: str, company2_ticker: str) -> Dict:
    """
    Analyze EUMR compliance for a potential merger between two specific companies.

    Parameters:
    -----------
    company1_ticker: Stock ticker of first company
    company2_ticker: Stock ticker of second company

    Returns:
    --------
    Dict containing detailed EUMR compliance analysis
    """

    def get_company_financials(ticker: str) -> Dict:
        """Helper function to get company financials"""
        company = yf.Ticker(ticker)
        info = company.info
        financials = company.financials

        if financials.empty:
            raise ValueError(f"Could not fetch financial data for {ticker}")

        # Get the most recent yearly revenue (turnover)
        latest_financials = financials.iloc[:, 0]
        total_revenue = latest_financials.get('Total Revenue', 0)

        # Get market capitalization
        market_cap = info.get('marketCap', 0)

        # Try to get geographical revenue breakdown
        try:
            geo_revenue = company.get_geographical_revenue()
        except:
            geo_revenue = None

        return {
            'name': info.get('longName', ticker),
            'ticker': ticker,
            'total_revenue': total_revenue,
            'market_cap': market_cap,
            'geo_revenue': geo_revenue,
            'currency': info.get('currency', 'USD')
        }

    def calculate_eu_revenue(revenue: float, geo_revenue: Optional[pd.DataFrame] = None) -> Tuple[float, Dict]:
        """Estimate EU revenue based on available geographical data"""
        if geo_revenue is not None and not geo_revenue.empty:
            # Try to find EU specific revenue
            eu_regions = ['Europe', 'EU', 'EMEA']
            eu_revenue = 0
            for region in eu_regions:
                if region in geo_revenue.index:
                    eu_revenue = geo_revenue.loc[region]
                    break
        else:
            # If no geographical breakdown, estimate EU revenue as 30% of total
            eu_revenue = revenue * 0.30

        return eu_revenue, {'eu_revenue_estimated': geo_revenue is None}

    try:
        # Get both companies' data
        company1_data = get_company_financials(company1_ticker)
        company2_data = get_company_financials(company2_ticker)

        # Calculate EU revenues for both companies
        company1_eu_revenue, company1_eu_notes = calculate_eu_revenue(
            company1_data['total_revenue'],
            company1_data.get('geo_revenue')
        )

        company2_eu_revenue, company2_eu_notes = calculate_eu_revenue(
            company2_data['total_revenue'],
            company2_data.get('geo_revenue')
        )

        # Calculate combined figures
        combined_worldwide_revenue = company1_data['total_revenue'] + company2_data['total_revenue']
        combined_eu_revenue = company1_eu_revenue + company2_eu_revenue
        combined_market_cap = company1_data['market_cap'] + company2_data['market_cap']

        # Convert to euros for EUMR thresholds
        eur_usd_rate = 1.1  # Should be updated with current rate
        combined_worldwide_eur = combined_worldwide_revenue / eur_usd_rate
        company1_eu_eur = company1_eu_revenue / eur_usd_rate
        company2_eu_eur = company2_eu_revenue / eur_usd_rate

        # Check primary thresholds (Article 1(2))
        primary_threshold_met = (
            combined_worldwide_eur > 5_000_000_000 and  # €5 billion worldwide
            company1_eu_eur > 250_000_000 and          # €250 million EU (company 1)
            company2_eu_eur > 250_000_000              # €250 million EU (company 2)
        )

        # Check alternative thresholds (Article 1(3))
        alternative_threshold_met = (
            combined_worldwide_eur > 2_500_000_000 and  # €2.5 billion worldwide
            company1_eu_eur > 100_000_000 and          # €100 million EU (company 1)
            company2_eu_eur > 100_000_000              # €100 million EU (company 2)
            # Note: Cannot check 3-member state criterion without detailed country breakdown
        )

        # Prepare detailed analysis
        analysis = {
            'company1': {
                'name': company1_data['name'],
                'ticker': company1_data['ticker'],
                'worldwide_revenue': company1_data['total_revenue'],
                'eu_revenue': company1_eu_revenue,
                'market_cap': company1_data['market_cap'],
                'eu_revenue_notes': company1_eu_notes
            },
            'company2': {
                'name': company2_data['name'],
                'ticker': company2_data['ticker'],
                'worldwide_revenue': company2_data['total_revenue'],
                'eu_revenue': company2_eu_revenue,
                'market_cap': company2_data['market_cap'],
                'eu_revenue_notes': company2_eu_notes
            },
            'combined_metrics': {
                'worldwide_revenue_usd': combined_worldwide_revenue,
                'worldwide_revenue_eur': combined_worldwide_eur,
                'eu_revenue_eur': combined_eu_revenue / eur_usd_rate,
                'combined_market_cap': combined_market_cap
            },
            'eumr_analysis': {
                'primary_threshold_met': primary_threshold_met,
                'alternative_threshold_met': alternative_threshold_met,
                'notification_required': primary_threshold_met or alternative_threshold_met,
                'thresholds': {
                    'primary': {
                        'worldwide_revenue': 5_000_000_000,
                        'eu_revenue': 250_000_000
                    },
                    'alternative': {
                        'worldwide_revenue': 2_500_000_000,
                        'eu_revenue': 100_000_000
                    }
                },
                'notes': [
                    "Analysis based on most recent financial data",
                    "EU revenue estimates may need verification",
                    "Three-member state criterion requires detailed country breakdown",
                    "Exchange rates should be verified at time of transaction",
                    f"Current EUR/USD rate used: {eur_usd_rate}"
                ]
            }
        }

        return analysis

    except Exception as e:
        raise ValueError(f"Error performing EUMR analysis: {str(e)}")

def generate_merger_report(analysis: Dict) -> str:
    """
    Generate a formatted report of the merger EUMR compliance analysis.
    """
    report = f"""
Merger EUMR Compliance Analysis Report
====================================

Company 1: {analysis['company1']['name']} ({analysis['company1']['ticker']})
-------------------------------------------------------------------------
Worldwide Revenue: ${analysis['company1']['worldwide_revenue']:,.2f}
EU Revenue: ${analysis['company1']['eu_revenue']:,.2f}
Market Cap: ${analysis['company1']['market_cap']:,.2f}
{' (EU Revenue Estimated)' if analysis['company1']['eu_revenue_notes']['eu_revenue_estimated'] else ''}

Company 2: {analysis['company2']['name']} ({analysis['company2']['ticker']})
-------------------------------------------------------------------------
Worldwide Revenue: ${analysis['company2']['worldwide_revenue']:,.2f}
EU Revenue: ${analysis['company2']['eu_revenue']:,.2f}
Market Cap: ${analysis['company2']['market_cap']:,.2f}
{' (EU Revenue Estimated)' if analysis['company2']['eu_revenue_notes']['eu_revenue_estimated'] else ''}

Combined Metrics
--------------
Worldwide Revenue (USD): ${analysis['combined_metrics']['worldwide_revenue_usd']:,.2f}
Worldwide Revenue (EUR): €{analysis['combined_metrics']['worldwide_revenue_eur']:,.2f}
Combined EU Revenue (EUR): €{analysis['combined_metrics']['eu_revenue_eur']:,.2f}
Combined Market Cap: ${analysis['combined_metrics']['combined_market_cap']:,.2f}

EUMR Compliance Analysis
----------------------
Primary Threshold (€5B worldwide, €250M EU each): {'Met' if analysis['eumr_analysis']['primary_threshold_met'] else 'Not Met'}
Alternative Threshold (€2.5B worldwide, €100M EU each): {'Met' if analysis['eumr_analysis']['alternative_threshold_met'] else 'Not Met'}

EUMR Notification Required: {'YES' if analysis['eumr_analysis']['notification_required'] else 'NO'}

Important Notes:
{chr(10).join('- ' + note for note in analysis['eumr_analysis']['notes'])}
"""
    return report

# Example usage
if __name__ == "__main__":
    try:
        # Analyze potential merger between Microsoft and Adobe
        #analysis = analyze_merger_eumr_compliance('MSFT', 'ADBE')
        analysis = analyze_merger_eumr_compliance('MSFT', 'AAPL')
        print(generate_merger_report(analysis))

    except ValueError as e:
        print(f"Error: {str(e)}")