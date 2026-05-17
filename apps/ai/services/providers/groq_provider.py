import os
from groq import Groq
from .base_provider import BaseProvider
from ..exceptions import AIProviderError
from ..ai_logger import ai_logger

class GroqProvider(BaseProvider):
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key or api_key == 'your_api_key_here':
            raise AIProviderError("GROQ_API_KEY is not configured.")
        
        self.client = Groq(api_key=api_key)

    def generate_response(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        try:
            # For JSON enforcement in parsing fallback, or standard chat
            response_format = kwargs.get("response_format")
            model = kwargs.get("model", "llama-3.3-70b-versatile")
            
            ai_logger.debug(f"Requesting generation from Groq ({model}).")

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            params = {
                "model": model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.3),
                "max_tokens": kwargs.get("max_tokens", 1500)
            }

            if response_format:
                params["response_format"] = response_format

            response = self.client.chat.completions.create(**params)
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            ai_logger.error(f"GroqProvider Error: {e}", exc_info=True)
            raise AIProviderError(f"Groq API Error: {str(e)}")
