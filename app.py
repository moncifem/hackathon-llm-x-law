import os
from dotenv import load_dotenv
import streamlit as st
from services.product_extractor import ProductExtractorService
from utils.constants import COMPANY_URLS
from services.ticker_evaluation import find_ticker, analyze_merger_eumr_compliance, generate_merger_report
import json

# Load environment variables from .env
load_dotenv()

def load_companies():
    """Load companies from the JSON file"""
    try:
        with open('companies_data.json', 'r') as f:
            data = json.load(f)
            companies = {k: v for category in data.values() 
                       for k, v in category.items()}
            return {k.title(): v for k, v in companies.items()}
    except FileNotFoundError:
        st.error("companies_data.json file not found!")
        return {}
    except json.JSONDecodeError:
        st.error("Error reading companies data file!")
        return {}

def get_openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please set it in a `.env` file.")
        raise ValueError("OpenAI API key is missing.")
    return api_key

def get_company_info(company_name):
    """Get company ticker information"""
    ticker_results = find_ticker(company_name)
    if ticker_results and ticker_results[0][0] != "Error":
        return ticker_results[0]  # Returns (ticker, full_name)
    return None, None

def format_market_cap(value):
    """Format market cap value for better readability"""
    if value >= 1_000_000_000_000:  # Trillion
        return f"${value/1_000_000_000_000:.2f}T"
    elif value >= 1_000_000_000:  # Billion
        return f"${value/1_000_000_000:.2f}B"
    elif value >= 1_000_000:  # Million
        return f"${value/1_000_000:.2f}M"
    else:
        return f"${value:,.2f}"

# Main application
st.set_page_config(page_title="Company Product Extractor", layout="wide")

# Load companies data
COMPANIES = load_companies()

# Sidebar Configuration
st.sidebar.title("Configuration")

# Create two columns in the sidebar for company selection
col1, col2 = st.sidebar.columns(2)

with col1:
    company1 = st.selectbox(
        "Select First Company",
        options=list(COMPANIES.keys()),
        index=None,
        key="company1",
        placeholder="Choose first company..."
    )

with col2:
    available_companies2 = [comp for comp in COMPANIES.keys() if comp != company1]
    company2 = st.selectbox(
        "Select Second Company",
        options=available_companies2,
        index=None,
        key="company2",
        placeholder="Choose second company..."
    )

# Main Page
st.title("🔍 Company Product Analyzer")

# Initialize Product Extractor Service
try:
    openai_api_key = get_openai_api_key()
    extractor = ProductExtractorService(openai_api_key)
except ValueError as e:
    st.error(str(e))
    st.stop()

# Only proceed if both companies are selected
if company1 and company2:
    if st.button("Analyze Selected Companies"):
        # First, get ticker information for both companies
        ticker1, full_name1 = get_company_info(company1)
        ticker2, full_name2 = get_company_info(company2)

        # Display company information section
        st.header("Company Information")
        info_col1, info_col2 = st.columns(2)

        with info_col1:
            st.subheader(f"{company1}")
            if ticker1 and full_name1:
                st.markdown(f"""
                - **Full Name:** {full_name1}
                - **Ticker Symbol:** {ticker1}
                """)
            else:
                st.warning(f"Could not find ticker information for {company1}")

        with info_col2:
            st.subheader(f"{company2}")
            if ticker2 and full_name2:
                st.markdown(f"""
                - **Full Name:** {full_name2}
                - **Ticker Symbol:** {ticker2}
                """)
            else:
                st.warning(f"Could not find ticker information for {company2}")

        # Add EUMR Compliance Analysis
        if ticker1 and ticker2:
            st.header("EUMR Compliance Analysis")
            with st.spinner("Analyzing EUMR compliance..."):
                try:
                    # Perform EUMR analysis
                    analysis = analyze_merger_eumr_compliance(ticker1, ticker2)
                    report = generate_merger_report(analysis)
                    
                    # Display the report in a formatted way
                    st.markdown("### Merger EUMR Compliance Report")
                    st.markdown("---")
                    
                    # Create expandable section for detailed report
                    with st.expander("View Detailed EUMR Analysis", expanded=True):
                        # Split the report into sections for better formatting
                        sections = report.split('\n\n')
                        for section in sections:
                            if section.strip():
                                st.markdown(section)
                    
                    # Quick summary at the top
                    st.info(f"EUMR Notification Required: {'YES' if analysis['eumr_analysis']['notification_required'] else 'NO'}")
                    
                    # Display Combined Market Cap
                    st.header("Combined Market Capitalization")
                    combined_market_cap = analysis['combined_metrics']['combined_market_cap']
                    
                    # Display market caps using metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            label=f"{company1} Market Cap",
                            value=format_market_cap(analysis['company1']['market_cap'])
                        )
                    with col2:
                        st.metric(
                            label=f"{company2} Market Cap",
                            value=format_market_cap(analysis['company2']['market_cap'])
                        )
                    with col3:
                        st.metric(
                            label="Combined Market Cap",
                            value=format_market_cap(combined_market_cap)
                        )
                    
                except Exception as e:
                    st.error(f"Error in EUMR analysis: {str(e)}")

            st.markdown("---")  # Add a separator line

            # Proceed with product analysis
            results = {}
            
            with st.spinner("Analyzing Products..."):
                # Analyze both selected companies
                for company, ticker in [(company1, ticker1), (company2, ticker2)]:
                    st.write(f"**Analyzing {company} ({ticker})**")
                    urls = COMPANY_URLS[company]
                    
                    all_text = ""
                    for url in urls:
                        text = extractor.scrape_webpage(url)
                        if text:
                            all_text += text + "\n\n"
                    
                    products = extractor.extract_products_with_llm(company, all_text)
                    results[company] = {
                        'ticker': ticker,
                        'full_name': full_name1 if company == company1 else full_name2,
                        'products': products
                    }

            # Display Products Section
            st.header("Product Analysis Results")
            prod_col1, prod_col2 = st.columns(2)
            
            with prod_col1:
                st.subheader(f"{company1} Products")
                if company1 in results:
                    st.write("\n".join(f"- {product}" for product in results[company1]['products']))
            
            with prod_col2:
                st.subheader(f"{company2} Products")
                if company2 in results:
                    st.write("\n".join(f"- {product}" for product in results[company2]['products']))

            # Download JSON with all results including EUMR analysis
            combined_results = {
                'company_info': results,
                'eumr_analysis': analysis if 'analysis' in locals() else None
            }
            
            st.download_button(
                "Download Complete Analysis (JSON)",
                data=json.dumps(combined_results, indent=2),
                file_name="company_analysis.json",
                mime="application/json"
            )
        else:
            st.error("Could not proceed with analysis due to missing ticker information.")
else:
    st.info("Please select two different companies to compare.")