from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """Create the chat model once from settings and reuse it for every request."""
    return ChatGoogleGenerativeAI(model=settings.llm_model, google_api_key=settings.gemini_api_key.get_secret_value(), temperature=settings.llm_temperature, timeout=settings.llm_timeout_seconds, max_retries=2)
