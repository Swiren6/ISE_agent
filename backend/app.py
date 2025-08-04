import os
import logging
from flask import Flask,jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()

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
            "origins": ["*"],
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Initialisation base de données
    from config.database import init_db
    init_db(app)
    
    # Enregistrement des routes
    from routes.auth import auth_bp
    from routes.agent import agent_bp
    app.register_blueprint(auth_bp, url_prefix='/api')
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