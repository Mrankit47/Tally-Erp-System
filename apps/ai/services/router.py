from .providers import GeminiProvider, DeepSeekProvider, GroqProvider
from .exceptions import AIProviderError
from .ai_logger import ai_logger

class AIRouter:
    def __init__(self):
        # Lazy initialization of providers to avoid crashing on import if keys are missing
        self._gemini = None
        self._deepseek = None
        self._groq = None

    def get_gemini(self):
        if not self._gemini:
            self._gemini = GeminiProvider()
        return self._gemini

    def get_deepseek(self):
        if not self._deepseek:
            self._deepseek = DeepSeekProvider()
        return self._deepseek

    def get_groq(self):
        if not self._groq:
            self._groq = GroqProvider()
        return self._groq

    def route_request(self, task: str, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        Routes the AI request to the specified provider based on the task type.
        Implements fallback mechanisms if the primary provider fails.
        """
        if task == "invoice":
            try:
                ai_logger.info("Routing 'invoice' task to Gemini Provider.")
                return self.get_gemini().generate_response(system_prompt, user_prompt, **kwargs)
            except Exception as e:
                ai_logger.error(f"Gemini provider failed for invoice task after all model fallbacks: {e}.")
                raise AIProviderError("All Gemini models failed to parse the invoice.")

        elif task == "finance":
            try:
                ai_logger.info("Routing 'finance' task to DeepSeek Provider.")
                return self.get_deepseek().generate_response(system_prompt, user_prompt, **kwargs)
            except Exception as e:
                ai_logger.warning(f"DeepSeek provider failed for finance task: {e}. Falling back to Groq.")
                # Fallback to Groq
                kwargs['model'] = "llama-3.3-70b-versatile"
                return self.get_groq().generate_response(system_prompt, user_prompt, **kwargs)

        elif task == "chat":
            try:
                ai_logger.info("Routing 'chat' task to Groq Provider.")
                kwargs['model'] = "llama-3.3-70b-versatile"
                return self.get_groq().generate_response(system_prompt, user_prompt, **kwargs)
            except Exception as e:
                ai_logger.error(f"Groq provider failed for chat task: {e}.")
                # Ultimate safe error
                return "I am currently unable to process your request due to an AI service outage. Please try again later."

        else:
            ai_logger.error(f"Unknown AI task type requested: {task}")
            raise ValueError(f"Unknown AI task type: {task}")

# Singleton instance
ai_router = AIRouter()
