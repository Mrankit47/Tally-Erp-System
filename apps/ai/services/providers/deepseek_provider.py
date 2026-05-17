import os
import requests
from .base_provider import BaseProvider
from ..exceptions import AIProviderError
from ..ai_logger import ai_logger

class DeepSeekProvider(BaseProvider):
    def __init__(self):
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise AIProviderError("OPENROUTER_API_KEY is not configured.")
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def generate_response(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        try:
            ai_logger.debug("Requesting generation from DeepSeek via OpenRouter (deepseek/deepseek-r1).")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://erp.internal", # Required by OpenRouter
                "X-Title": "Tally ERP System", # Required by OpenRouter
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek/deepseek-r1",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": kwargs.get("temperature", 0.2),
                "max_tokens": kwargs.get("max_tokens", 1500)
            }

            response = requests.post(self.endpoint, headers=headers, json=payload, timeout=60)
            response.raise_for_status()

            data = response.json()
            if "choices" not in data or len(data["choices"]) == 0:
                raise AIProviderError("Invalid response format from OpenRouter.")
                
            return data["choices"][0]["message"]["content"].strip()
            
        except requests.exceptions.RequestException as e:
            ai_logger.error(f"DeepSeekProvider Request Error: {e}")
            raise AIProviderError(f"OpenRouter Network Error: {str(e)}")
        except Exception as e:
            ai_logger.error(f"DeepSeekProvider Error: {e}", exc_info=True)
            raise AIProviderError(f"OpenRouter API Error: {str(e)}")
