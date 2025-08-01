

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
import logging
import traceback
from config.database import init_db, get_db, get_db_connection
import os

agent_bp = Blueprint('agent_bp', __name__)
logger = logging.getLogger(__name__)

# Initialisation assistant avec gestion d'erreurs
assistant = None
# def initialize_assistant():
#     global assistant
#     try:
#         from agent.assistant import SQLAssistant
#         from langchain_community.utilities import SQLDatabase
        
#         # Utiliser SQLDatabase de langchain
#         db_uri = f"mysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DATABASE')}"
#         db = SQLDatabase.from_uri(db_uri)
        
#         assistant = SQLAssistant(db)
#         print("✅ Assistant initialisé avec succès")
#         return True
        
#     except Exception as e:
#         print(f"❌ Erreur initialisation: {e}")
#         return False

def initialize_assistant():
    global assistant
    try:
        from agent.assistant import SQLAssistant
        from langchain_community.utilities import SQLDatabase
        assistant = SQLAssistant() 
        required_vars = ['MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_HOST', 'MYSQL_DATABASE', 'TOGETHER_API_KEY']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            print(f"❌ Variables manquantes: {missing}")
            return False
        
        # Utiliser SQLDatabase de langchain
        db_uri = f"mysql://{os.getenv('MYSQL_USER')}:{os.getenv('MYSQL_PASSWORD')}@{os.getenv('MYSQL_HOST')}/{os.getenv('MYSQL_DATABASE')}"
        db = SQLDatabase.from_uri(db_uri)
        
        assistant = SQLAssistant(db)
        print("✅ Assistant initialisé avec succès")
        return True
        
    except Exception as e:
        print(f"❌ Erreur initialisation: {e}")
        traceback.print_exc()  # ✅ AJOUT pour debug
        return False
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
            # sql_query, response = assistant.ask_question(question)
            
            # result = {
            #     "sql_query": sql_query,
            #     "response": response,
            #     "status": "success",
            #     "question": question
            # }
            response_data = assistant.get_response(question)

            result = {
                "response": response_data.get("response"),
                "sql_query": response_data.get("sql_query"),
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
        
@agent_bp.route('/test', methods=['GET'])
def test_simple():
    """Simple test endpoint"""
    return jsonify({
        "message": "Agent backend is working",
        "assistant_ready": assistant is not None,
        "timestamp": "2024-01-01T00:00:00Z"
    })
    
    
@agent_bp.route('/debug', methods=['GET'])
def debug():
    try:
        from agent.assistant import SQLAssistant
        db = get_db_connection()
        return jsonify({
            "db_connection": "OK" if db else "FAILED",
            "SQLAssistant_import": "OK",
            "env_vars": {
                "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
                "DB_CONNECTION": bool(os.getenv("DB_HOST"))
            }
        })
    except Exception as e:
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500