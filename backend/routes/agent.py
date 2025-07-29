# from flask import Blueprint, request, jsonify
# from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
# import logging
# import traceback
# from config.database import init_db, get_db,get_db_connection


# agent_bp = Blueprint('agent_bp', __name__)
# logger = logging.getLogger(__name__)

# # Initialisation assistant
# assistant = None
# try:
#     from agent.assistant import SQLAssistant
#     from config.database import get_db

#     assistant = SQLAssistant(db=get_db())


#     if assistant and assistant.db:
#         print("✅ Connexion DB disponible dans assistant")
#     else:
#         print("❌ Connexion DB manquante dans assistant")

#     print("✅ Assistant chargé avec succès")
# except Exception as e:
#     print(f"❌ Erreur assistant: {e}")
#     assistant = None

# @agent_bp.route('/ask', methods=['POST'])
# def ask_sql():  
        
#     # 🔧 Gestion JWT manuelle et optionnelle
#     jwt_valid = False
#     current_user = None
    
#     try:
#         # Essayer de vérifier le JWT si présent
#         if 'Authorization' in request.headers:
#             print("🔑 Token JWT détecté, vérification...")
#             verify_jwt_in_request(optional=True)
#             current_user = get_jwt_identity()
#             jwt_valid = True
#             print(f"✅ JWT valide pour utilisateur: {current_user}")
#         else:
#             print("ℹ️ Pas de token JWT, accès anonyme")
#     except Exception as jwt_error:
#         print(f"⚠️ Erreur JWT (ignorée): {jwt_error}")
#         # On continue sans JWT
    
#     try:
#         # Validation JSON
#         if not request.is_json:
#             print("❌ Pas de JSON")
#             return jsonify({"error": "JSON requis"}), 415
        
#         # Récupération données
#         data = request.get_json()
#         print(f"🔍 Données reçues: {data}")
#         # print(f"🔍 Utilisateur: {current_user if jwt_valid else 'Anonyme'}")
        
#         if not data:
#             print("❌ Données vides")
#             return jsonify({"error": "Pas de données"}), 400
        
#         # Recherche de la question
#         question = None
#         field_found = None
        
#         possible_fields = ['question', 'subject', 'query', 'text', 'message', 'prompt']
#         for field in possible_fields:
#             if field in data:
#                 value = data[field]
#                 print(f"🔍 Champ '{field}' trouvé: {value} (type: {type(value)})")
#                 if value and str(value).strip():
#                     question = str(value).strip()
#                     field_found = field
#                     break
        
#         # print(f"🎯 Question finale: '{question}' (depuis champ: {field_found})")
        
#         if not question:
#             print("❌ Aucune question trouvée")
#             return jsonify({
#                 "error": "Question manquante",
#                 "received_fields": list(data.keys()),
#                 "msg": "Aucune question valide trouvée"
#             }), 422
        
#         # Vérification assistant
#         if not assistant:
#             print("❌ Assistant indisponible")
#             return jsonify({"error": "Assistant indisponible"}), 503
        
#         print(f"🚀 Traitement: '{question}'")
        
#         # Traitement    
#         try:
#             sql_query, response = assistant.ask_question(question)
#             print(f"✅ Succès: SQL={sql_query}")
            
#             result = {
#                 "sql_query": sql_query,
#                 "response": response,
#                 "status": "success"
#             }
            
#             # Ajouter info utilisateur si JWT valide
#             if jwt_valid:
#                 result["user"] = current_user
            
#             return jsonify(result), 200
            
#         except Exception as e:
#             print(f"❌ Erreur traitement: {e}")
#             print(f"❌ Traceback: {traceback.format_exc()}")
#             return jsonify({
#                 "error": "Erreur traitement",
#                 "msg": str(e)
#             }), 500
        
#     except Exception as e:
#         print(f"❌ Erreur générale: {e}")
#         print(f"❌ Traceback: {traceback.format_exc()}")
#         return jsonify({
#             "error": "Erreur serveur",
#             "msg": str(e)
#         }), 500
        
# @agent_bp.route('/ask', methods=['GET'])
# def ask_info():
#     """Information sur l'endpoint"""
#     return jsonify({
#         "message": "Assistant IA pour questions scolaires",
#         "method": "POST",
#         "format": {"question": "Votre question ici"},
#         "status": "OK" if assistant else "ERROR"
#     })

# @agent_bp.route('/health', methods=['GET'])
# def health():
#     """Vérification de santé"""
#     return jsonify({
#         "status": "OK",
#         "assistant": "OK" if assistant else "ERROR"
#     })


from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
import logging
import traceback
from config.database import init_db, get_db, get_db_connection

agent_bp = Blueprint('agent_bp', __name__)
logger = logging.getLogger(__name__)

# Initialisation assistant avec gestion d'erreurs
assistant = None

def initialize_assistant():
    """Initialise l'assistant avec gestion d'erreurs"""
    global assistant
    try:
        from agent.assistant import SQLAssistant
        
        # Tentative d'initialisation
        assistant = SQLAssistant()
        
        if assistant and assistant.db:
            print("✅ Assistant initialisé avec succès")
            return True
        else:
            print("❌ Assistant initialisé mais DB manquante")
            return False
            
    except Exception as e:
        print(f"❌ Erreur initialisation assistant: {e}")
        assistant = None
        return False

# Initialisation au chargement du module
initialize_assistant()

@agent_bp.route('/ask', methods=['POST'])
def ask_sql():
    """Endpoint principal avec gestion d'erreurs robuste"""
    
    # Gestion JWT optionnelle
    jwt_valid = False
    current_user = None
    
    try:
        if 'Authorization' in request.headers:
            verify_jwt_in_request(optional=True)
            current_user = get_jwt_identity()
            jwt_valid = True
    except Exception:
        pass  # JWT optionnel
    
    try:
        # Validation JSON
        if not request.is_json:
            return jsonify({"error": "Content-Type application/json requis"}), 415
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Corps de requête JSON vide"}), 400
        
        # Extraction de la question
        question = None
        possible_fields = ['question', 'subject', 'query', 'text', 'message', 'prompt']
        
        for field in possible_fields:
            if field in data and data[field] and str(data[field]).strip():
                question = str(data[field]).strip()
                break
        
        if not question:
            return jsonify({
                "error": "Question manquante",
                "expected_fields": possible_fields,
                "received_fields": list(data.keys())
            }), 422
        
        # Vérification assistant
        if not assistant:
            # Tentative de réinitialisation
            if not initialize_assistant():
                return jsonify({
                    "error": "Assistant non disponible",
                    "details": "Impossible d'initialiser l'assistant IA"
                }), 503
        
        # Traitement de la question
        try:
            sql_query, response = assistant.ask_question(question)
            
            result = {
                "sql_query": sql_query,
                "response": response,
                "status": "success",
                "question": question
            }
            
            if jwt_valid:
                result["user"] = current_user
            
            return jsonify(result), 200
            
        except Exception as processing_error:
            logger.error(f"Erreur traitement: {processing_error}")
            return jsonify({
                "error": "Erreur de traitement",
                "details": str(processing_error),
                "question": question
            }), 500
        
    except Exception as e:
        logger.error(f"Erreur générale: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": "Erreur serveur interne",
            "details": str(e)
        }), 500

@agent_bp.route('/ask', methods=['GET'])
def ask_info():
    """Information sur l'endpoint"""
    return jsonify({
        "message": "Assistant IA pour questions scolaires",
        "method": "POST",
        "format": {"question": "Votre question ici"},
        "status": "OK" if assistant else "ERROR",
        "assistant_available": assistant is not None
    })

@agent_bp.route('/health', methods=['GET'])
def health():
    """Vérification de santé détaillée"""
    health_status = {
        "status": "OK",
        "assistant": "OK" if assistant else "ERROR",
        "database": "OK" if assistant and assistant.db else "ERROR",
        "timestamp": "2024-01-01T00:00:00Z"  # Vous pouvez ajouter datetime.utcnow().isoformat()
    }
    
    status_code = 200 if assistant else 503
    return jsonify(health_status), status_code

@agent_bp.route('/reinit', methods=['POST'])
def reinitialize():
    """Endpoint pour réinitialiser l'assistant"""
    try:
        success = initialize_assistant()
        return jsonify({
            "success": success,
            "message": "Réinitialisation réussie" if success else "Échec de la réinitialisation"
        }), 200 if success else 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500