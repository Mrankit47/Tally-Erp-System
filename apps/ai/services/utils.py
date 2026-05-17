import json
import re

def extract_json_from_text(text: str) -> dict:
    """
    Cleans up dirty LLM JSON outputs (e.g. removing markdown ```json)
    and attempts to parse the result.
    """
    text = text.strip()
    
    # Remove markdown code blocks if present
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
        
    text = text.strip()

    # Sometimes the model adds leading text before the JSON block.
    # Try to extract just the first JSON object or array.
    try:
        # First naive attempt
        return json.loads(text)
    except json.JSONDecodeError:
        # Try regex extraction
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        raise ValueError("Could not extract valid JSON from the provided text.")
