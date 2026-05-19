import os
import requests
from .base_provider import BaseProvider
from ..exceptions import AIProviderError
from ..ai_logger import ai_logger

class GeminiProvider(BaseProvider):
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise AIProviderError("GEMINI_API_KEY is not configured.")
        
        # List of stable models to try in order (waterfall fallback)
        self.fallback_models = [
            'gemini-2.0-flash',
            'gemini-2.5-flash',
            'gemini-1.5-flash',
            'gemini-1.5-pro'
        ]

    def generate_response(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        # standard text merge for systemic prompting over REST
        full_prompt = f"{system_prompt}\n\nUser Input:\n{user_prompt}"
        
        temperature = kwargs.get("temperature", 0.1)
        max_tokens = kwargs.get("max_tokens", 8000) # Support high output limits safely
        
        last_error = None

        for model_name in self.fallback_models:
            try:
                ai_logger.debug(f"Requesting generation from Gemini REST API ({model_name}).")
                
                # Official Google Gen AI REST endpoint
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
                
                headers = {
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": full_prompt
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens
                    }
                }
                
                # Make standard lightweight HTTP request with a 60 second timeout
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                if response.status_code != 200:
                    raise AIProviderError(f"HTTP Error {response.status_code}: {response.text}")
                    
                response_data = response.json()
                
                # Safely extract text from official Gemini REST schema
                candidates = response_data.get("candidates", [])
                if not candidates:
                    feedback = response_data.get("promptFeedback", {})
                    if feedback.get("blockReason"):
                        raise AIProviderError(f"Prompt blocked due to safety: {feedback}")
                    raise AIProviderError("No response candidates returned from Gemini REST API.")
                    
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if not parts:
                    raise AIProviderError("Empty content parts in Gemini REST response.")
                    
                text_response = parts[0].get("text", "")
                return text_response.strip()
                
            except Exception as e:
                last_error = e
                ai_logger.warning(f"Gemini REST model {model_name} failed: {e}. Falling back to next model...")

        # If we exhausted all models in the fallback chain
        ai_logger.error(f"All Gemini REST fallback models failed. Last error: {last_error}", exc_info=True)
        raise AIProviderError(f"Gemini REST API Error across all fallback models. Last Error: {str(last_error)}")
