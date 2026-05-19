import os
import google.generativeai as genai
from .base_provider import BaseProvider
from ..exceptions import AIProviderError
from ..ai_logger import ai_logger

class GeminiProvider(BaseProvider):
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise AIProviderError("GEMINI_API_KEY is not configured.")
        
        genai.configure(api_key=api_key)
        # List of models to try in order (waterfall fallback)
        self.fallback_models = [
            'gemini-2.0-flash',
            'gemini-2.5-flash',
            'gemini-flash-latest',
            'gemini-pro-latest',
            'gemini-3-flash-preview'
        ]

    def generate_response(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        # Using simple text merge for robustness with Gemini text APIs
        full_prompt = f"{system_prompt}\n\nUser Input:\n{user_prompt}"
        
        # Default to low temperature for deterministic tasks like JSON extraction
        temperature = kwargs.get("temperature", 0.1)
        
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=kwargs.get("max_tokens", 1500)
        )

        last_error = None

        for model_name in self.fallback_models:
            try:
                ai_logger.debug(f"Requesting generation from Gemini ({model_name}).")
                model = genai.GenerativeModel(model_name)
                
                response = model.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                    transport="rest"
                )

                if response.prompt_feedback and getattr(response.prompt_feedback, "block_reason", None):
                    ai_logger.error(f"Gemini {model_name} prompt blocked: {response.prompt_feedback}")
                    raise AIProviderError(f"Gemini {model_name} blocked the prompt due to safety filters.")

                return response.text.strip()
                
            except Exception as e:
                last_error = e
                ai_logger.warning(f"Gemini model {model_name} failed: {e}. Falling back to next model...")

        # If we exhausted all models in the fallback chain
        ai_logger.error(f"All Gemini fallback models failed. Last error: {last_error}", exc_info=True)
        raise AIProviderError(f"Gemini API Error across all fallback models. Last Error: {str(last_error)}")
