from openai import OpenAI
from typing import List, Dict


class OpenAIService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def chat_response(self, messages: List[Dict[str, str]]) -> str:
        """Fetches a chat response."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error: {str(e)}"
