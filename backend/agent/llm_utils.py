from openai import OpenAI
import os

def ask_llm(prompt: str) -> str:
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2048,
            timeout=60
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Erreur LLM: {str(e)}")
        return ""

# from openai import OpenAI
# import os
# import logging

# logger = logging.getLogger(__name__)

# def ask_llm(prompt: str) -> str:
#     """
#     SOLUTION IMMÉDIATE: Passage à GPT-4o-mini (128k tokens)
#     """
#     if not prompt or not prompt.strip():
#         logger.warning("Prompt vide reçu")
#         return ""
    
#     api_key = os.getenv("OPENAI_API_KEY")
#     if not api_key:
#         logger.error("❌ OPENAI_API_KEY manquante")
#         return ""
    
#     try:
#         client = OpenAI(api_key=api_key)
        
#         # CHANGEMENT CRITIQUE: GPT-4o-mini au lieu de GPT-3.5-turbo
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",  # 128k tokens au lieu de 16k
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.1,
#             max_tokens=2048,
#             timeout=60  # Plus de temps pour GPT-4
#         )
        
#         result = response.choices[0].message.content
#         if not result:
#             logger.warning("Réponse LLM vide")
#             return ""
            
#         logger.info("✅ Réponse LLM reçue (GPT-4o-mini)")
#         return result.strip()
        
#     except Exception as e:
#         logger.error(f"❌ Erreur LLM: {str(e)}")
#         return ""