import os
from dotenv import load_dotenv
import streamlit as st
from services.product_extractor import ProductExtractorService
from utils.constants import COMPANY_URLS
import json

# Load environment variables from .env
load_dotenv()

# Function to retrieve the OpenAI API key
def get_openai_api_key():
    # First, try to fetch the key from environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please set it in a `.env` file.")
        raise ValueError("OpenAI API key is missing.")
    return api_key

# Main application
st.set_page_config(page_title="Company Product Extractor", layout="wide")

# Sidebar Configuration
st.sidebar.title("Configuration")
selected_companies = st.sidebar.multiselect(
    "Select Companies", options=list(COMPANY_URLS.keys()), default=["Microsoft", "Apple"]
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

if st.button("Analyze Selected Companies"):
    results = {}

    with st.spinner("Analyzing..."):
        for company in selected_companies:
            st.write(f"**Analyzing {company}**")
            urls = COMPANY_URLS[company]

            all_text = ""
            for url in urls:
                text = extractor.scrape_webpage(url)
                if text:
                    all_text += text + "\n\n"

            # Process text in chunks
            products = extractor.extract_products_with_llm(company, all_text)
            results[company] = products

    # Display Results
    st.subheader("Results")
    for company, products in results.items():
        st.write(f"### {company}")
        st.write("\n".join(f"- {product}" for product in products))

    # Download JSON
    st.download_button(
        "Download Results (JSON)",
        data=json.dumps(results, indent=2),
        file_name="company_products.json",
        mime="application/json"
    )
