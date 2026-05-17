import logging
from .router import ai_router

logger = logging.getLogger('apps.ai')

def ask_ai(message: str, company, context_data: str, language: str = 'English') -> str:
    """
    Sends a message to the AI Chatbot using the centralized AI Router.
    """
    try:
        if language.lower() == 'hinglish':
            lang_instruction = "RESPOND STRICTLY IN HINGLISH (Hindi/English mix written in Roman script, e.g., 'Aapka total profit ₹50,000 hai aur expenses ₹20,000 hain, toh net profit kafi achha chal raha hai.'). NEVER use Devanagari script or Hindi letters. Output the entire response in clean, conversational Hinglish."
        else:
            lang_instruction = f"RESPOND STRICTLY IN THE FOLLOWING LANGUAGE: {language}. Write the entire reply using this language (e.g., if language is Hindi, output in Hindi script; if Tamil, in Tamil script; if Marathi, in Marathi script; etc.). Keep all ERP numbers, calculations, and concepts accurate, but translate the explanation completely."

        system_prompt = f"""You are a friendly, professional ERP financial assistant specialized in accounting, GST, invoices, and business insights.

RULES:
1. You are answering questions for the company: {company.name}.
2. Use the provided [LIVE ERP DATA] to answer the user's question.
3. NEVER output placeholder text like "[Name will be inserted]". Read the actual data.
4. NEVER mention SQL, databases, memory snapshots, or how you got the data.
5. Be conversational, polite, and clear. Use Markdown for formatting (bolding, lists).
6. If the user asks something completely unrelated to business, accounting, or the ERP, politely decline.
7. {lang_instruction}
"""

        user_content = message
        if context_data:
             user_content = f"""[LIVE ERP DATA]
{context_data}

[USER QUESTION]
{message}"""

        logger.debug("Routing chat request to AI router for 'chat' task.")
        
        reply = ai_router.route_request(
            task="chat",
            system_prompt=system_prompt,
            user_prompt=user_content,
            temperature=0.3,
            max_tokens=1024
        )
        
        return reply

    except Exception as e:
        logger.error(f"Unexpected error in ask_ai: {e}", exc_info=True)
        return "Sorry, I encountered an error while processing your request with the AI service."
