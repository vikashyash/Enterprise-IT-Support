import logging

from functools import lru_cache
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings
import os
from dotenv import load_dotenv
load_dotenv()

logger=logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_chat_model()->BaseChatModel:
    try:
        return ChatGoogleGenerativeAI(model=settings.llm_model,google_api_key=os.getenv("GEMINI_API_KEY",""),temperature=settings.llm_temperature, timeout=settings.llm_timeout_seconds, max_retries=2)
    except Exception:
        logger.exception("Could not create chat model for provider %s")
        raise