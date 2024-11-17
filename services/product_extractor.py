import requests
from bs4 import BeautifulSoup
import trafilatura
from openai import OpenAI
from typing import List, Dict, Set


class ProductExtractorService:
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def scrape_webpage(self, url: str) -> str:
        """Scrapes a webpage and extracts its textual content."""
        try:
            downloaded = trafilatura.fetch_url(url)
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
            if not text:
                response = requests.get(url, headers=self.headers)
                soup = BeautifulSoup(response.text, 'html.parser')
                for element in soup(['script', 'style', 'nav', 'footer']):
                    element.decompose()
                text = ' '.join(soup.stripped_strings)
            return text or ""
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return ""

    def extract_products_with_llm(self, company: str, text: str) -> List[str]:
        """Uses an OpenAI LLM to extract products from text."""
        prompt = f"""
        Analyze the following text and list {company}'s products/services:
        Include:
        - Hardware, software, cloud, subscription services, and platforms.
        Only significant and confirmed items.
        Text: {text[:4000]}
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000
            )
            return [line.strip('- ').strip() for line in response.choices[0].message.content.split('\n') if line.strip()]
        except Exception as e:
            print(f"Error in LLM processing: {str(e)}")
            return []
