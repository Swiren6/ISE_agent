from flask import Blueprint, request, jsonify
from flask_jwt_extended import  get_jwt_identity,verify_jwt_in_request
import logging
import traceback
import datetime
from routes.auth import login
from services.auth_service import AuthService

agent_bp = Blueprint('agent_bp', __name__)
logger = logging.getLogger(__name__)


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
            jwt_valid = True if current_user else False
            logger.debug(f"Current user data: {current_user}")
    except Exception as e:
        logger.warning(f"JWT verification warning: {str(e)}")
        current_user = None
    
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
            # Gestion sécurisée du current_user
            user_id = current_user.get('idpersonne') if current_user and isinstance(current_user, dict) else None
            roles = current_user.get('roles', []) if current_user and isinstance(current_user, dict) else []
            
            # Juste avant d'appeler assistant.ask_question():
            logger.debug(f"[Before ask_question] user_id: {user_id}, roles: {roles}") 
            sql_query, response = assistant.ask_question(question, user_id, roles)
            
            result = {
                "sql_query": sql_query,
                "response": response,
                "status": "success",
                "question": question
            }
            
            if jwt_valid and current_user:
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
        "timestamp": "2024-01-01T00:00:00Z"  
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

