from flask_mysqldb import MySQL
from langchain_community.utilities import SQLDatabase
import MySQLdb
from urllib.parse import quote_plus
import os
import logging
from dotenv import load_dotenv
import mysql.connector as mysql_connector



from contextlib import contextmanager
load_dotenv()
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
        app.config['MYSQL_AUTOCOMMIT'] = True
        app.config['MYSQL_CONNECT_TIMEOUT'] = 60
        
        # Validation des variables d'environnement
        required_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Variables d'environnement manquantes: {missing_vars}")
        
        mysql.init_app(app)
        
        # ✅ Test de connexion immédiat
        test_connection = create_direct_connection()
        if test_connection:
            test_connection.close()
            logger.info("✅ Configuration MySQL initialisée et testée")
        else:
            raise Exception("Impossible de se connecter à MySQL")
            
        return mysql
    except Exception as e:
        logger.error(f"❌ Erreur init MySQL: {e}")
        raise

def create_direct_connection():
    """Crée une connexion MySQL directe (indépendante de Flask)"""
    try:
        connection = MySQLdb.connect(
            host=os.getenv('MYSQL_HOST'),
            user=os.getenv('MYSQL_USER'),
            passwd=os.getenv('MYSQL_PASSWORD'),
            db=os.getenv('MYSQL_DATABASE'),
            cursorclass=MySQLdb.cursors.DictCursor,
            autocommit=True,
            connect_timeout=10
        )
        # ✅ Marquer comme connexion directe pour savoir quand la fermer
        connection._direct_connection = True
        logger.debug("✅ Connexion MySQL directe créée")
        return connection
    except Exception as e:
        logger.error(f"❌ Erreur connexion MySQL directe: {e}")
        return None

def get_db():
    """Returns a MySQL connection - uses Flask connection if available, otherwise creates a direct connection"""
    try:
        # First try Flask connection
        from flask import current_app
        if current_app and hasattr(current_app, 'extensions') and 'mysql' in current_app.extensions:
            mysql_connection = current_app.extensions['mysql'].connection
            if mysql_connection:
                # Test connection
                try:
                    cursor = mysql_connection.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                    logger.debug("✅ Using existing Flask MySQL connection")
                    return mysql_connection
                except Exception as test_error:
                    logger.warning(f"⚠️ Flask connection test failed: {test_error}")
                    # Continue to create new connection
    except Exception as e:
        logger.warning(f"⚠️ Flask context check failed: {e}")

    # Fallback to direct connection
    logger.info("🔄 Creating new direct MySQL connection")
    return create_direct_connection()


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


class ExtendedSQLDatabase(SQLDatabase):
    def __init__(self, engine, **kwargs):
        super().__init__(engine, **kwargs)
        self.config = {
            'host': os.getenv('MYSQL_HOST'),
            'user': os.getenv('MYSQL_USER'),
            'password': os.getenv('MYSQL_PASSWORD'),
            'database': os.getenv('MYSQL_DATABASE'),
        }

    def get_schema(self):
        try:
            return self.run("SHOW TABLES")
        except Exception as e:
            logger.error(f"Erreur get_schema : {e}")
            return {}
    def get_connection(self):
        try:
            conn = mysql_connector.connect(**self.config)

            conn.ping(reconnect=True)
            logger.info("[🔗] Connexion à la base de données établie.")
            return conn
        except mysql.connector.Error as err:
            logger.error(f"[❌] Erreur MySQL: {err}")
            raise

    def execute_query(self, query, params=None, fetch=True):
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            logger.info(f"[SQL EXECUTE] Requête exécutée:\n{query}")
            if params:
                logger.info(f"[SQL PARAMS] Paramètres: {params}")
            
            cursor.execute(query, params or ())
            if fetch:
                results = cursor.fetchall()
                conn.commit()
                logger.info(f"[SQL RESULT] {len(results)} lignes retournées")
                return {'success': True, 'data': results}
            conn.commit()
            return {'success': True}
        except Exception as e:
            logger.error(f"[SQL ERROR] Erreur d'exécution: {e}")
            return {'success': False, 'error': str(e)}
        finally:
            cursor.close()
            conn.close()

    def get_simplified_relations_text(self):
        try:
            fk_relations = self.get_foreign_key_relations()
            simplified = {}
            for row in fk_relations:
                table = row['TABLE_NAME']
                referenced_table = row['REFERENCED_TABLE_NAME']
                if table not in simplified:
                    simplified[table] = set()
                simplified[table].add(referenced_table)

            lines = ["Relations clés principales entre tables :\n"]
            for table, references in simplified.items():
                line = f"- {table} liée à " + ", ".join(sorted(references)) + "."
                lines.append(line)
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Erreur get_simplified_relations_text : {e}")
            return ""
    

