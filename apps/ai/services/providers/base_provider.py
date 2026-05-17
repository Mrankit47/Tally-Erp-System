from abc import ABC, abstractmethod

class BaseProvider(ABC):
    """Abstract base class for all AI providers."""

    @abstractmethod
    def generate_response(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        Generate a text response given a system prompt and a user prompt.
        """
        pass
