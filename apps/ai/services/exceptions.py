class AIProviderError(Exception):
    """Raised when an AI provider fails to generate a response."""
    pass

class AIParsingError(Exception):
    """Raised when the AI response cannot be parsed into the expected format."""
    pass
