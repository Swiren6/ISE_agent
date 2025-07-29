from openai import OpenAI
import os

def ask_llm(prompt: str) -> str:
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Erreur LLM: {str(e)}")
        return ""


# import requests
# import os
# import logging
# from typing import Optional

# logger = logging.getLogger(__name__)

# def ask_llm(prompt: str, api_key: Optional[str] = None) -> str:
#     """
#     Version robuste avec gestion de clé API et fallback
#     """
#     if not prompt.strip():
#         logger.warning("Prompt vide reçu")
#         return ""

#     # Configuration de l'API DeepSeek
#     url = "https://api.deepseek.com/v1/chat/completions"
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {api_key or os.getenv('DEEPSEEK_API_KEY')}"
#     }
    
#     payload = {
#         "model": "deepseek-chat",
#         "messages": [{"role": "user", "content": prompt}],
#         "temperature": 0.1,
#         "max_tokens": 2048
#     }

#     try:
#         response = requests.post(
#             url,
#             headers=headers,
#             json=payload,
#             timeout=30
#         )
        
#         # Gestion spécifique des erreurs HTTP
#         if response.status_code == 401:
#             logger.error("❌ Clé API DeepSeek invalide/missing")
#             return ""
#         response.raise_for_status()

#         result = response.json().get('choices', [{}])[0].get('message', {}).get('content', "")
#         return result.strip() if result else ""

#     except requests.exceptions.RequestException as e:
#         logger.error(f"❌ Erreur API: {str(e)}")
#         return ""