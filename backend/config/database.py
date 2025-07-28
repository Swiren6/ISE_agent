from flask_mysqldb import MySQL
from langchain_community.utilities import SQLDatabase
from urllib.parse import quote_plus
import os

mysql = MySQL()

def init_db(app):
    """Initialise la configuration MySQL pour Flask"""
    app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
    app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
    app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
    app.config['MYSQL_DB'] = os.getenv('MYSQL_DATABASE')
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
    
    mysql.init_app(app)
    return mysql

def get_db():
    """Retourne la connexion MySQL pour Flask (pour les routes)"""
    return mysql.connection

def get_db_connection():
    """Retourne une instance SQLDatabase de LangChain (pour l'assistant)"""
    db_user = os.getenv('MYSQL_USER')
    db_password = quote_plus(os.getenv('MYSQL_PASSWORD'))
    db_host = os.getenv('MYSQL_HOST')
    db_name = os.getenv('MYSQL_DATABASE')
    
    db_uri = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
    return SQLDatabase.from_uri(db_uri)