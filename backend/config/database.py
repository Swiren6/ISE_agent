from flask_mysqldb import MySQL
from langchain_community.utilities import SQLDatabase
import MySQLdb
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
        app.config['MYSQL_AUTOCOMMIT'] = True
        app.config['MYSQL_CONNECT_TIMEOUT'] = 10
        
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
    """Retourne la connexion MySQL - utilise d'abord Flask, puis connexion directe"""
    try:
        # ✅ Essayer d'abord la connexion Flask
        from flask import current_app
        if current_app and hasattr(mysql, 'connection') and mysql.connection:
            # Test rapide de la connexion Flask
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            logger.debug("✅ Connexion Flask MySQL OK")
            return mysql.connection
    except Exception as e:
        logger.warning(f"⚠️ Connexion Flask MySQL échouée: {e}")
    
    # ✅ Fallback vers connexion directe
    logger.info("🔄 Utilisation connexion MySQL directe")
    return create_direct_connection()

# def get_db_connection():
#     """Retourne une instance SQLDatabase de LangChain (pour l'assistant)"""
#     try:
#         db_user = os.getenv('MYSQL_USER')
#         db_password = quote_plus(os.getenv('MYSQL_PASSWORD'))
#         db_host = os.getenv('MYSQL_HOST')
#         db_name = os.getenv('MYSQL_DATABASE')
        
#         # Validation
#         if not all([db_user, db_password, db_host, db_name]):
#             raise ValueError("Variables de connexion DB manquantes")
        
#         db_uri = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
#         db = SQLDatabase.from_uri(db_uri)
        
#         # Test de connexion
#         db.run("SELECT 1")
#         logger.info("✅ Connexion LangChain SQLDatabase établie")
#         return db
        
#     except Exception as e:
#         logger.error(f"❌ Erreur connexion LangChain: {e}")
#         return None

# def get_db_connection():
#     """Retourne une instance SQLDatabase personnalisée (pour l'assistant)"""
#     try:
#         db_user = os.getenv('MYSQL_USER')
#         db_password = quote_plus(os.getenv('MYSQL_PASSWORD'))
#         db_host = os.getenv('MYSQL_HOST')
#         db_name = os.getenv('MYSQL_DATABASE')

#         if not all([db_user, db_password, db_host, db_name]):
#             raise ValueError("Variables de connexion DB manquantes")

#         db_uri = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
#         db = ExtendedSQLDatabase.from_uri(db_uri)

#         # Test de connexion
#         db.run("SELECT 1")
#         logger.info("✅ Connexion LangChain SQLDatabase établie")
#         return db

#     except Exception as e:
#         logger.error(f"❌ Erreur connexion LangChain: {e}")
#         return None


# def get_db_connection():
#     """Retourne une instance SQLDatabase personnalisée (pour l'assistant)"""
#     try:
#         db_user = os.getenv('MYSQL_USER')
#         db_password = os.getenv('MYSQL_PASSWORD')  # Remove quote_plus
#         db_host = os.getenv('MYSQL_HOST')
#         db_name = os.getenv('MYSQL_DATABASE')

#         if not all([db_user, db_password, db_host, db_name]):
#             logger.error("Missing database connection variables")
#             raise ValueError("Variables de connexion DB manquantes")

#         # Use standard MySQL connector if LangChain fails
#         try:
#             import pymysql
#             conn = pymysql.connect(
#                 host=db_host,
#                 user=db_user,
#                 password=db_password,
#                 database=db_name
#             )
#             return conn
#         except ImportError:
#             logger.warning("PyMySQL not available, trying SQLDatabase")
            
#         db_uri = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
#         db = ExtendedSQLDatabase.from_uri(db_uri)
#         db.run("SELECT 1")
#         logger.info("✅ Connexion LangChain SQLDatabase établie")
#         return db

#     except Exception as e:
#         logger.error(f"❌ Erreur connexion DB: {e}")
#         raise RuntimeError(f"Database connection failed: {str(e)}")

def get_db_connection():
    try:
        db_user = os.getenv('MYSQL_USER')
        db_password = os.getenv('MYSQL_PASSWORD')
        db_host = os.getenv('MYSQL_HOST')
        db_name = os.getenv('MYSQL_DATABASE')

        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Variables de connexion DB manquantes")

        db_uri = f"mysql+pymysql://{db_user}:{db_password}@{db_host}/{db_name}"
        db = ExtendedSQLDatabase.from_uri(db_uri)
        db.run("SELECT 1")
        logger.info("✅ Connexion LangChain SQLDatabase établie")
        return db

    except Exception as e:
        logger.error(f"❌ Erreur connexion DB: {e}")
        raise RuntimeError(f"Database connection failed: {str(e)}")

class ExtendedSQLDatabase(SQLDatabase):
    def get_schema(self):
        try:
            result = self.run("SHOW TABLES")
            # Convertir le résultat en liste de noms de tables
            if isinstance(result, str):
                # Si c'est une chaîne, extraire les noms de tables
                tables = [line.strip() for line in result.split('\n') if line.strip()]
                return tables
            return result
        except Exception as e:
            logger.error(f"Erreur get_schema : {e}")
            return []

    # AJOUTEZ CETTE MÉTHODE MANQUANTE
    def get_foreign_key_relations(self):
        """Récupère les relations de clés étrangères"""
        try:
            query = """
            SELECT 
                TABLE_NAME,
                COLUMN_NAME,
                CONSTRAINT_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE REFERENCED_TABLE_SCHEMA = DATABASE()
            AND REFERENCED_TABLE_NAME IS NOT NULL
            """
            result = self.run(query)
            
            # Analyser le résultat et le convertir en format attendu
            relations = []
            if isinstance(result, str):
                lines = result.strip().split('\n')
                for line in lines[1:]:  # Skip header
                    parts = line.split('\t') if '\t' in line else line.split('|')
                    if len(parts) >= 5:
                        relations.append({
                            'TABLE_NAME': parts[0].strip(),
                            'COLUMN_NAME': parts[1].strip(),
                            'CONSTRAINT_NAME': parts[2].strip(),
                            'REFERENCED_TABLE_NAME': parts[3].strip(),
                            'REFERENCED_COLUMN_NAME': parts[4].strip()
                        })
            
            return relations
        except Exception as e:
            logger.error(f"Erreur get_foreign_key_relations : {e}")
            return []

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

    # AJOUTEZ CETTE MÉTHODE POUR EXÉCUTER LES REQUÊTES
    def execute_query(self, sql, params=None):
        """Exécute une requête SQL et retourne le résultat formaté"""
        try:
            if params:
                # LangChain SQLDatabase ne supporte pas les paramètres de cette façon
                # On doit faire l'échappement manuellement (attention à la sécurité)
                result = self.run(sql)
            else:
                result = self.run(sql)
            
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f"❌ Erreur SQL execute_query: {e}")
            return {'success': False, 'error': str(e)}