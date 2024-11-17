import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-3.5-turbo"

# Streamlit page settings
PAGE_TITLE = "AI Chatbot"
PAGE_ICON = "🤖"

# Chat settings
MAX_MESSAGES = 50
SYSTEM_PROMPT = """You are a helpful AI assistant. Respond concisely and clearly to user questions."""