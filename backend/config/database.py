# from flask_mysqldb import MySQL
# from langchain_community.utilities import SQLDatabase
# from urllib.parse import quote_plus
# import os

# mysql = MySQL()

# def init_db(app):
#     """Initialise la configuration MySQL pour Flask"""
#     app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
#     app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
#     app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
#     app.config['MYSQL_DB'] = os.getenv('MYSQL_DATABASE')
#     app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
    
#     mysql.init_app(app)
#     return mysql

# def get_db():
#     """Retourne la connexion MySQL pour Flask (pour les routes)"""
#     return mysql.connection

# def get_db_connection():
#     """Retourne une instance SQLDatabase de LangChain (pour l'assistant)"""
#     db_user = os.getenv('MYSQL_USER')
#     db_password = quote_plus(os.getenv('MYSQL_PASSWORD'))
#     db_host = os.getenv('MYSQL_HOST')
#     db_name = os.getenv('MYSQL_DATABASE')
    
#     db_uri = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
#     return SQLDatabase.from_uri(db_uri)
from flask_mysqldb import MySQL
from langchain_community.utilities import SQLDatabase
from urllib.parse import quote_plus
import os
import logging

mysql = MySQL()
logger = logging.getLogger(__name__)

def init_db(app):
    """Initialise la configuration MySQL pour Flask"""
    try:
        app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
        app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
        app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
        app.config['MYSQL_DB'] = os.getenv('MYSQL_DATABASE')
        app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
        
        # Validation des variables d'environnement
        required_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Variables d'environnement manquantes: {missing_vars}")
        
        mysql.init_app(app)
        logger.info("✅ Configuration MySQL initialisée")
        return mysql
    except Exception as e:
        logger.error(f"❌ Erreur init MySQL: {e}")
        raise

def get_db():
    """Retourne la connexion MySQL pour Flask (pour les routes)"""
    try:
        return mysql.connection
    except Exception as e:
        logger.error(f"❌ Erreur connexion Flask MySQL: {e}")
        return None

def get_db_connection():
    """Retourne une instance SQLDatabase de LangChain (pour l'assistant)"""
    try:
        db_user = os.getenv('MYSQL_USER')
        db_password = quote_plus(os.getenv('MYSQL_PASSWORD'))
        db_host = os.getenv('MYSQL_HOST')
        db_name = os.getenv('MYSQL_DATABASE')
        
        # Validation
        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Variables de connexion DB manquantes")
        
        db_uri = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
        db = SQLDatabase.from_uri(db_uri)
        
        # Test de connexion
        db.run("SELECT 1")
        logger.info("✅ Connexion LangChain SQLDatabase établie")
        return db
        
    except Exception as e:
        logger.error(f"❌ Erreur connexion LangChain: {e}")
        return None