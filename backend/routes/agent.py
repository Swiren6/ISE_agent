
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
import time
import logging
import traceback
from config.database import init_db, get_db, get_db_connection
import re 
from agent.sql_agent import SQLAgent 
from agent.pdf_utils.attestation import export_attestation_pdf
import os
agent_bp = Blueprint('agent_bp', __name__)
logger = logging.getLogger(__name__)

# Initialisation assistant avec gestion d'erreurs
assistant = None
engine = SQLAgent(get_db_connection())
def validate_name(full_name):
    """Valide le format du nom"""
    return bool(re.match(r'^[A-Za-zÀ-ÿ\s\-\']{3,50}$', full_name))

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
        if "attestation" in question.lower():
            
            name_match = re.search(
                r"(?:attestation\s+(?:de|pour)\s+)([A-Za-zÀ-ÿ\s\-\']+)", 
                question, 
                re.IGNORECASE
            )
            
            if not name_match:
                return jsonify({
                    "response": "Veuillez spécifier un nom (ex: 'attestation de Nom Prénom')"
                })

            full_name = name_match.group(1).strip()
            
            if not validate_name(full_name):
                return jsonify({
                    "response": "Format de nom invalide. Utilisez uniquement des lettres et espaces"
                })
            print(f"Recherche élève pour nom complet : {full_name}")



            # Récupération des données
            student_data = engine.get_student_info_by_name(full_name)
            
            print(f"Résultat de recherche: {student_data}")
            
            if not student_data:
                return jsonify({
                    "response": f"Aucun élève trouvé avec le nom '{full_name}'"
                })

            # Harmoniser les champs pour le PDF
            student_data['nom_complet'] = student_data['nom']
            student_data['lieu_naissance'] = student_data['lieu_de_naissance']
            student_data['annee_scolaire'] = "2024/2025"


            # Génération du PDF
            try:
                pdf_path = export_attestation_pdf(student_data)

                filename = os.path.basename(pdf_path)
                
                return jsonify({
                "response": (
                    f"✅ Attestation générée pour {student_data['nom_complet']}\n\n"
                    f"<a href='/static/attestations/{filename}' download>Télécharger</a>"
                ),
                "pdf_url": f"/static/attestations/{filename}"
            })

            except Exception as e:
                logger.error(f"Erreur génération PDF: {str(e)}")
                return jsonify({
                    "response": "Erreur lors de la génération du document"
                })

        try:
            sql_query, response = assistant.ask_question(question)

            # 🔥 Exécution de la requête SQL
            try:
                rows = engine.execute_natural_query(sql_query)  # Doit retourner List[Dict]
            except Exception as e:
                logger.error(f"Erreur d'exécution SQL : {e}")
                return jsonify({
                    "error": "Erreur d'exécution SQL",
                    "sql_query": sql_query,
                    "details": str(e)
                }), 500

            result = {
                "sql_query": sql_query,
                "response": response,
                "status": "success",
                "question": question,
                "data": rows
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

@agent_bp.route('/ask', methods=['GET'])  # Doit correspondre au POST
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