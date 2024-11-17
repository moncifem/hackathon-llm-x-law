import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
from services.product_extractor import ProductExtractorService
from utils.constants import COMPANY_URLS
from services.ticker_evaluation import find_ticker, analyze_merger_eumr_compliance, generate_merger_report
from services.openai_service import OpenAIService
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

def compare_products(products1, products2, company1, company2):
    """Compare products and find similar products between companies"""
    openai_service = OpenAIService(get_openai_api_key())
    
    categorization_prompt = f"""
    Analyze these two lists of products and create a detailed comparison identifying similar products and their categories:

    {company1} Products:
    {chr(10).join('- ' + p for p in products1)}

    {company2} Products:
    {chr(10).join('- ' + p for p in products2)}

    Create a comparison following these steps:
    1. Group products into these categories:
       - Computing Devices (PCs, laptops, tablets)
       - Mobile Devices (phones, smartphones)
       - Operating Systems
       - Cloud Services
       - Enterprise Software
       - Productivity Software
       - Gaming Products
       - AI/ML Solutions
       - Hardware Components
       - Other (specify category)

    2. For each category, list the competing products from both companies.
    3. Format as a markdown table with columns:
       | Category | {company1} Products | {company2} Products |

    Only include categories where both companies have competing products.
    Match products that serve similar purposes even if named differently.
    """

    messages = [
        {"role": "system", "content": """You are a product analysis expert. 
        Focus on matching similar products across companies, even if they have different names. 
        Consider functionality and target market when matching products.
        Be specific in identifying competing products."""},
        {"role": "user", "content": categorization_prompt}
    ]

    categorized_comparison = openai_service.chat_response(messages)

    competitive_prompt = f"""
    Based on the same product lists, provide a competitive analysis:
    1. Key areas of direct competition
    2. Strengths of each company in competing categories
    3. Unique product offerings for each company
    
    Format this as a clear, bulleted analysis.
    """

    messages.append({"role": "user", "content": competitive_prompt})
    competitive_analysis = openai_service.chat_response(messages)

    return categorized_comparison, competitive_analysis

def analyze_innovation_and_skills(products1, products2, company1, company2):
    """Analyze innovation and technical skills for both companies"""
    openai_service = OpenAIService(get_openai_api_key())
    
    innovation_prompt = f"""
    Based on these product lists, analyze the innovation profile of both companies:

    {company1} Products:
    {chr(10).join('- ' + p for p in products1)}

    {company2} Products:
    {chr(10).join('- ' + p for p in products2)}

    Please provide:
    1. Key innovation areas for each company
    2. Core technological competencies
    3. Notable R&D achievements
    4. Patent-heavy domains (if apparent from products)
    5. Innovation trajectory and future potential

    Format as a detailed markdown analysis with clear sections for each company.
    """

    skills_prompt = f"""
    Based on the same product lists, analyze the technical skills and expertise required:

    1. Create a comprehensive list of technical skills for each company, including:
       - Programming languages
       - Frameworks
       - Hardware expertise
       - Domain knowledge
       - Specialized technical skills

    2. Identify overlapping skills between companies
    3. List unique technical capabilities for each company
    4. Note any specialized industry knowledge

    Format as a clear markdown list with separate sections for each company.
    """

    knowhow_prompt = f"""
    Analyze the institutional knowledge and expertise evident from these products:

    1. Core competencies and specialized knowledge areas
    2. Industry-specific expertise
    3. Manufacturing and production capabilities
    4. Quality control and testing expertise
    5. Supply chain and logistics knowledge
    6. Customer service and support capabilities

    Provide a comparative analysis highlighting strengths and unique capabilities.
    Format in markdown with clear sections for each company.
    """

    messages = [
        {"role": "system", "content": "You are a technology industry analyst specializing in innovation assessment and technical capabilities analysis."},
        {"role": "user", "content": innovation_prompt}
    ]
    innovation_analysis = openai_service.chat_response(messages)

    messages = [{"role": "user", "content": skills_prompt}]
    skills_analysis = openai_service.chat_response(messages)

    messages = [{"role": "user", "content": knowhow_prompt}]
    knowhow_analysis = openai_service.chat_response(messages)

    return innovation_analysis, skills_analysis, knowhow_analysis

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
st.title("Company Product Analyzer")

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
        analysis = analyze_merger_eumr_compliance(ticker1, ticker2)
        report = generate_merger_report(analysis)

        if ticker1 and ticker2:
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

            st.header("EUMR Compliance Analysis")
            with st.spinner("Analyzing EUMR compliance..."):
                try:
                    st.markdown("---")
                    with st.expander("View Detailed EUMR Analysis", expanded=True):
                        sections = report.split('\n\n')
                        for section in sections:
                            if section.strip():
                                st.markdown(section)
                    st.info(f"EUMR Notification Required: {'YES' if analysis['eumr_analysis']['notification_required'] else 'NO'}")
                except Exception as e:
                    st.error(f"Error in EUMR analysis: {str(e)}")

            st.markdown("---")

            # Product Analysis
            results = {}
            with st.spinner("Analyzing Products..."):
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

            # Product Comparison Section
            st.header("Product Portfolio Comparison")
            if company1 in results and company2 in results:
                with st.spinner("Analyzing product portfolios..."):
                    # Get comparison results
                    categorized_comparison, competitive_analysis = compare_products(
                        results[company1]['products'],
                        results[company2]['products'],
                        company1,
                        company2
                    )
                    
                    with st.expander("🔄 Product Category Comparison", expanded=True):
                        st.markdown(categorized_comparison)
                    
                    with st.expander("📊 Competitive Analysis", expanded=True):
                        st.markdown(competitive_analysis)

                # Innovation and Technical Capabilities Analysis
                st.header("Innovation and Technical Capabilities Analysis")
                with st.spinner("Analyzing innovation and technical capabilities..."):
                    innovation_analysis, skills_analysis, knowhow_analysis = analyze_innovation_and_skills(
                        results[company1]['products'],
                        results[company2]['products'],
                        company1,
                        company2
                    )
                    
                    with st.expander("🔍 Innovation Analysis", expanded=True):
                        st.markdown(innovation_analysis)
                    
                    with st.expander("💡 Technical Skills Comparison", expanded=True):
                        st.markdown(skills_analysis)
                    
                    with st.expander("🎯 Industry Knowhow and Expertise", expanded=True):
                        st.markdown(knowhow_analysis)

                    st.markdown("---")

            # Download JSON with all results
            combined_results = {
                'company_info': results,
                'eumr_analysis': analysis if 'analysis' in locals() else None,
                'product_comparison': {
                    'categorized_comparison': categorized_comparison if 'categorized_comparison' in locals() else None,
                    'competitive_analysis': competitive_analysis if 'competitive_analysis' in locals() else None,
                    'innovation_analysis': innovation_analysis if 'innovation_analysis' in locals() else None,
                    'skills_analysis': skills_analysis if 'skills_analysis' in locals() else None,
                    'knowhow_analysis': knowhow_analysis if 'knowhow_analysis' in locals() else None
                }
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