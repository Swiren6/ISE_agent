import json
import logging
from flask import current_app
<<<<<<< HEAD
from config.database import get_db  
import re
=======
from config.database import get_db
>>>>>>> 2f62f252ca35df8efbcc3aa92d70d941e87bb9d6

class AuthService:
    @staticmethod
    def parse_roles(raw_roles):
<<<<<<< HEAD
        current_app.logger.info(f"Raw roles received: {raw_roles} (type: {type(raw_roles)})")
        
=======
>>>>>>> 2f62f252ca35df8efbcc3aa92d70d941e87bb9d6
        if raw_roles is None:
            return []
        
        if isinstance(raw_roles, list):
            return raw_roles
        
        try:
<<<<<<< HEAD
            if isinstance(raw_roles, str) and raw_roles.startswith('["') and raw_roles.endswith('"]'):
                parsed = json.loads(raw_roles)
                return parsed
            
            if isinstance(raw_roles, str):
                parsed = json.loads(raw_roles)
                return parsed if isinstance(parsed, list) else [parsed]
                
=======
            parsed = json.loads(raw_roles)
            return parsed if isinstance(parsed, list) else [parsed]

>>>>>>> 2f62f252ca35df8efbcc3aa92d70d941e87bb9d6
        except json.JSONDecodeError as e:
            current_app.logger.warning(f"JSON decode failed: {str(e)}")
            return [raw_roles] if raw_roles else []
<<<<<<< HEAD
        
        return [raw_roles] if raw_roles else []
    
    
=======
>>>>>>> 2f62f252ca35df8efbcc3aa92d70d941e87bb9d6

    @staticmethod
    def authenticate_user(login_identifier, password):
        connection = None
        cursor = None
        
        try:
            current_app.logger.info(f"🔍 Tentative authentification: {login_identifier}")
            
            connection = get_db()
            
            if connection is None:
                current_app.logger.error("❌ Impossible d'obtenir une connexion DB")
                return None
                
            cursor = connection.cursor()
            current_app.logger.debug("✅ Curseur DB créé")

            # ✅ Requête avec logging
            query = """
                SELECT idpersonne, email, roles, changepassword 
                FROM user 
                WHERE email = %s OR idpersonne = %s
            """
            cursor.execute(query, (login_identifier, login_identifier))
            current_app.logger.debug(f"✅ Requête exécutée: {query}")

            user = cursor.fetchone()
            current_app.logger.debug(f"✅ Résultat DB: {'Utilisateur trouvé' if user else 'Aucun utilisateur'}")

            if not user:
                current_app.logger.warning(f"❌ Utilisateur non trouvé: {login_identifier}")
                return None

            roles = AuthService.parse_roles(user['roles'])

            current_app.logger.info(f"✅ Utilisateur authentifié: {user['idpersonne']} avec rôles: {roles}")
            
            return {
                'idpersonne': user['idpersonne'],
                'email': user['email'],
                'roles': roles,
                'changepassword': user['changepassword']
            }

        except Exception as e:
            current_app.logger.error(f"❌ Erreur authentification: {str(e)}")
            return None
<<<<<<< HEAD

=======
            
        finally:
            # ✅ Nettoyage des ressources
            if cursor:
                try:
                    cursor.close()
                    current_app.logger.debug("✅ Curseur fermé")
                except:
                    pass
                    
            # ✅ Fermer la connexion seulement si c'est une connexion directe
            if connection and hasattr(connection, '_direct_connection'):
                try:
                    connection.close()
                    current_app.logger.debug("✅ Connexion directe fermée")
                except:
                    pass
>>>>>>> 2f62f252ca35df8efbcc3aa92d70d941e87bb9d6
