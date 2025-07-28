import json
import logging
from flask import current_app
from config.database import get_db  # ✅ Correct import

class AuthService:
    @staticmethod
    # def parse_roles(raw_roles):
    #     current_app.logger.info(f"Raw roles received: {raw_roles} (type: {type(raw_roles)})")
        
    #     if raw_roles is None:
    #         return []
        
    #     if isinstance(raw_roles, list):
    #         return raw_roles
        
    #     try:
    #         if isinstance(raw_roles, str) and raw_roles.startswith('["') and raw_roles.endswith('"]'):
    #             parsed = json.loads(raw_roles)
    #             return parsed
            
    #         if isinstance(raw_roles, str):
    #             parsed = json.loads(raw_roles)
    #             return parsed if isinstance(parsed, list) else [parsed]
                
    #     except json.JSONDecodeError as e:
    #         current_app.logger.warning(f"JSON decode failed: {str(e)}")
    #         return [raw_roles] if raw_roles else []
        
    #     return [raw_roles] if raw_roles else []
    
    
    @staticmethod
    def parse_roles(raw_roles):
        # current_app.logger.info(f"Raw roles received: {raw_roles} (type: {type(raw_roles)})")
        
        if raw_roles is None:
            return []

        if isinstance(raw_roles, list):
            return raw_roles

        try:
            parsed = json.loads(raw_roles)
            # current_app.logger.info(f"Parsed roles: {parsed}")
            return parsed if isinstance(parsed, list) else [parsed]

        except json.JSONDecodeError as e:
            current_app.logger.error(f"❌ JSON decode failed: {str(e)}")
            return [raw_roles] if raw_roles else []





    @staticmethod
    def authenticate_user(login_identifier, password):
        try:
            connection = get_db()  # ✅ utilisation correcte
            cur = connection.cursor()

            cur.execute("""
                SELECT idpersonne, email, roles, changepassword 
                FROM user 
                WHERE email = %s OR idpersonne = %s
            """, (login_identifier, login_identifier))

            user = cur.fetchone()
            cur.close()

            if not user:
                return None

            roles = AuthService.parse_roles(user['roles'])

            return {
                'idpersonne': user['idpersonne'],
                'email': user['email'],
                'roles': roles,
                'changepassword': user['changepassword']
            }

        except Exception as e:
            current_app.logger.error(f"Error authenticating user: {str(e)}")
            return None
