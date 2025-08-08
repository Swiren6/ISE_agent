import os
import logging
from flask import Flask,jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
from dotenv import load_dotenv
from config.database import get_db


from routes.agent import agent_bp
# Chargement des variables d'environnement
load_dotenv(dotenv_path=r"C:/Users/rania/OneDrive/Bureau/ISE_agent/backend/.env")

# Validation de la configuration
required_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"❌ Variables manquantes: {missing_vars}")
    exit(1)

def create_app():
    """Factory pour créer l'application Flask"""
    app = Flask(__name__)
    jwt = JWTManager(app)
    # 🔧 Configuration JWT - CRITIQUE
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config['JWT_TOKEN_LOCATION'] = ['headers']
    
    # 🔧 AJOUT : Configuration JWT plus flexible
    app.config['JWT_HEADER_NAME'] = 'Authorization'
    app.config['JWT_HEADER_TYPE'] = 'Bearer'
    
    jwt = JWTManager(app)
    
    # 🔧 AJOUT : Gestion d'erreur JWT
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token expired"}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"error": "Invalid token"}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"error": "Token required"}), 401
    
    # Configuration CORS
    CORS(app, resources={
            r"/api/*": {
                "origins": ["http://localhost:*", "http://127.0.0.1:*"], 
                "methods": ["GET", "POST"],
                "allow_headers": ["*"]
            }
        })
    
    # Initialisation base de données
    from config.database import init_db
    init_db(app)
    
    # Enregistrement des routes
    from routes.auth import auth_bp
    from routes.agent import agent_bp
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(agent_bp,url_prefix='/api')


    
    @app.route('/api/notifications', methods=['GET'])
    def check_exam_notifications():
        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM notification_queue WHERE seen = 0")
            notifications_non_vues = cursor.fetchall()

            messages = [{"id": notif["id"], "message": notif["message"]} for notif in notifications_non_vues]


            if notifications_non_vues:
                ids = [str(notif['id']) for notif in notifications_non_vues]
                format_strings = ",".join(["%s"] * len(ids))
                update_query = f"UPDATE notification_queue SET seen = 1 WHERE id IN ({format_strings})"
                cursor.execute(update_query, ids)
                conn.commit()

            return jsonify(messages)

        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
            # Ne PAS fermer conn ici

    # Route de santé avec test DB
    @app.route('/api/health')
    def health():
        try:
            from config.database import get_db
            conn = get_db()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                cursor.close()
                if hasattr(conn, '_direct_connection'):
                    conn.close()
                return {"status": "OK", "database": "Connected", "test": result}
            else:
                return {"status": "OK", "database": "Disconnected"}, 503
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {"status": "ERROR", "database": str(e)}, 503
    
    # ✅ Route de test d'authentification
    @app.route('/api/test-db')
    def test_db():
        try:
            from config.database import get_db
            conn = get_db()
            if not conn:
                return {"error": "No database connection"}, 500
                
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM user")
            result = cursor.fetchone()
            cursor.close()
            
            if hasattr(conn, '_direct_connection'):
                conn.close()
                
            return {"status": "OK", "user_count": result['count']}
        except Exception as e:
            logger.error(f"❌ DB test failed: {e}")
            return {"error": str(e)}, 500
    return app 
    app.register_blueprint(agent_bp, url_prefix='/api')
    
    # Route de santé
    @app.route('/api/health')
    def health():
        return {"status": "OK"}
    
    return app

def main():
    """Point d'entrée principal"""
    # Configuration logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Création de l'application
    app = create_app()
    
    print("🚀 Assistant Scolaire - Backend démarré")
    print(f"📍 URL: http://localhost:5000")
    print(f"🏥 Health: http://localhost:5000/api/health")
    
    # Démarrage du serveur
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("👋 Serveur arrêté")

if __name__ == "__main__":
    main()