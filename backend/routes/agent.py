from flask import Blueprint, request, jsonify,g
from flask_jwt_extended import get_jwt_identity,verify_jwt_in_request,get_jwt, get_jwt_identity
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
    """Version corrigée pour lire le JWT avec claims"""
    
    jwt_valid = False
    current_user = None
    jwt_error = None
    
    try:
        if 'Authorization' in request.headers:
            try:
                verify_jwt_in_request(optional=True)
                
                # Récupération de l'identity (subject)
                jwt_identity = get_jwt_identity()  # Sera une string maintenant
                
                # Récupération des claims additionnels
                jwt_claims = get_jwt()
                
                print(f"DEBUG - JWT Identity: {jwt_identity}")
                print(f"DEBUG - JWT Claims: {jwt_claims}")
                
                # Construction de current_user
                if jwt_identity and jwt_claims:
                    current_user = {
                        'sub': jwt_identity,
                        'idpersonne': jwt_claims.get('idpersonne'),
                        'roles': jwt_claims.get('roles', []),
                        'username': jwt_claims.get('username', '')
                    }
                    jwt_valid = True
                    
            except Exception as jwt_exc:
                jwt_error = str(jwt_exc)
                print(f"DEBUG - Erreur JWT: {jwt_error}")
                current_user = None
                
    except Exception as e:
        jwt_error = str(e)
        print(f"DEBUG - Erreur générale JWT: {jwt_error}")
    
    try:
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
        
        user_id = current_user.get('idpersonne') if current_user else None
        roles = current_user.get('roles', []) if current_user else []
        
        print(f"DEBUG FINAL - user_id: {user_id}, roles: {roles}")
        
        # Vérification assistant
        if not assistant:
            if not initialize_assistant():
                return jsonify({
                    "error": "Assistant non disponible",
                    "details": "Impossible d'initialiser l'assistant IA"
                }), 503
        
        sql_query, response = assistant.ask_question(question, user_id, roles)
        
        result = {
            "sql_query": sql_query,
            "response": response,
            "status": "success",
            "question": question,
            "debug": {
                "jwt_valid": jwt_valid,
                "jwt_error": jwt_error,
                "user_id": user_id,
                "roles": roles
            }
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Erreur générale: {e}")
        return jsonify({
            "error": "Erreur serveur interne",
            "details": str(e)
        }), 500

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

