import os
import json
import logging
from groq import Groq

logger = logging.getLogger('apps.ai')

def ask_ai(message: str, company, context_data: str) -> str:
    """
    Sends a message to the Groq API using the official SDK.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == 'your_api_key_here':
        logger.error("GROQ_API_KEY is not set correctly.")
        return "I am currently unable to process your request due to missing API configuration."

    try:
        client = Groq(api_key=api_key)
        
        system_prompt = f"""You are a friendly, professional ERP financial assistant specialized in accounting, GST, invoices, and business insights.

RULES:
1. You are answering questions for the company: {company.name}.
2. Use the provided [LIVE ERP DATA] to answer the user's question.
3. NEVER output placeholder text like "[Name will be inserted]". Read the actual data.
4. NEVER mention SQL, databases, memory snapshots, or how you got the data.
5. Be conversational, polite, and clear. Use Markdown for formatting (bolding, lists).
6. If the user asks something completely unrelated to business, accounting, or the ERP, politely decline.
"""

        user_content = message
        if context_data:
             user_content = f"""[LIVE ERP DATA]
{context_data}

[USER QUESTION]
{message}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        logger.debug(f"Sending request to Groq with model llama-3.1-8b-instant")
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.3, # Low temp for factual financial answers
            max_tokens=1024,
        )
        
        reply = response.choices[0].message.content.strip()
        return reply

    except Exception as e:
        logger.error(f"Unexpected error in ask_ai: {e}")
        return "Sorry, I encountered an error while processing your request with the AI service."
