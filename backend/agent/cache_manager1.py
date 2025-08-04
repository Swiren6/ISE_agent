import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import hashlib
import re
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
from config.database import get_db
import traceback

logger = logging.getLogger(__name__)
class CacheManager1:
    def __init__(self, cache_file: str = "sql_query_cache1.json"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()

        
        # Patterns de base pour les valeurs structurées
        self.auto_patterns = {
            r'\b([A-Z]{3,})\s+([A-Z]{3,})\b': 'NomPrenom',
            r'\b\d+[A-Z]\d+\b': 'CODECLASSEFR', 
            r'\b(20\d{2}[/-]20\d{2})\b': 'AnneeScolaire',
            r'\b\d{1,5}\b': 'IDPersonne'
        }
        self.trimestre_mapping = {
            '1er trimestre': 31,
            '1ère trimestre': 31,
            'premier trimestre': 31,
            '2ème trimestre': 32,
            'deuxième trimestre': 32,
            '3ème trimestre': 33,
            '3éme trimestre': 33,
            'troisième trimestre': 33,
            'trimestre 1': 31,
            'trimestre 2': 32,
            'trimestre 3': 33
        }
        self.discovered_patterns = defaultdict(list)
        
        # Initialisation du vectorizer TF-IDF
        self.vectorizer = TfidfVectorizer()
        self.template_vectors = None
        self._init_similarity_search()

    def _init_similarity_search(self):
        """Initialise le système de recherche de similarité"""
        if self.cache:
            templates = [self._normalize_template(item['question_template']) 
                        for item in self.cache.values()]
            self.vectorizer.fit(templates)
            self.template_vectors = self.vectorizer.transform(templates)

    def _load_cache(self) -> Dict[str, Any]:
        if not self.cache_file.exists():
            return {}
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, indent=2, ensure_ascii=False)
        self._init_similarity_search()  # Recharge les vecteurs après sauvegarde

    def _extract_family_references(self, question: str) -> Dict[str, str]:
        """Détecte les références familiales et les normalise"""
        family_patterns = {
            r'\b(?:mon|ma|mes)\s+(enfant|fille|fils|enfants)\b': 'id_personne',
            r'\b(?:de|du|d\')\s*(?:mon|ma|mes)\s+(enfant|fille|fils|enfants)\b': 'id_personne',
            r'\bmon\s+enfant\b': 'id_personne',
            r'\bma\s+fille\b': 'id_personne', 
            r'\bmon\s+fils\b': 'id_personne',
            r'\bmes\s+enfants\b': 'id_personne'
        }
        
        family_refs = {}
        normalized_question = question.lower()
        
        for pattern, placeholder in family_patterns.items():
            if re.search(pattern, normalized_question, re.IGNORECASE):
                family_refs['family_relation'] = placeholder
                break
        
        return family_refs

    def _normalize_sql_for_family(self, sql_query: str, children_ids: List[int]) -> str:
        """Normalise le SQL en remplaçant les IDs enfants par des placeholders"""
        normalized_sql = sql_query
        
        if not children_ids:
            return normalized_sql
        
        # Convertir les IDs en strings pour les remplacements
        children_ids_str = [str(id) for id in children_ids]
        
        # Patterns pour remplacer les IDs spécifiques par des variables
        patterns_to_replace = [
            # WHERE clauses avec IdPersonne (un seul ID)
            (rf"\b(IdPersonne|e\.IdPersonne|eleve\.IdPersonne)\s*=\s*({'|'.join(children_ids_str)})\b", 
            r'\1 = {id_personne}'),
            
            # WHERE clauses avec IN (un seul ID)
            (rf"\b(IdPersonne|e\.IdPersonne|eleve\.IdPersonne)\s+IN\s*\(\s*({'|'.join(children_ids_str)})\s*\)", 
            r'\1 IN ({id_personne})'),
            
            # WHERE clauses avec IN (plusieurs IDs)
            (rf"\b(IdPersonne|e\.IdPersonne|eleve\.IdPersonne)\s+IN\s*\(\s*({',\s*'.join(children_ids_str)})\s*\)", 
            r'\1 IN ({id_personne})'),
        ]
        
        for pattern, replacement in patterns_to_replace:
            normalized_sql = re.sub(pattern, replacement, normalized_sql, flags=re.IGNORECASE)
        
        return normalized_sql
    
    def _extract_parameters(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Détection intelligente des paramètres"""
        variables = {}
        normalized = text

        family_refs = self._extract_family_references(text)
        if family_refs:
            # Remplacer toutes les références familiales par un placeholder uniforme
            family_patterns = [
                r'\b(?:mon|ma|mes)\s+(?:enfant|fille|fils|enfants)\b',
                r'\b(?:de|du|d\')\s*(?:mon|ma|mes)\s+(?:enfant|fille|fils|enfants)\b'
            ]
            
            for pattern in family_patterns:
                normalized = re.sub(pattern, '{family_relation}', normalized, flags=re.IGNORECASE)
            
            variables['id_personne'] = family_refs['family_relation']
        
        for term, code in self.trimestre_mapping.items():
            if term in normalized.lower():
                normalized = normalized.replace(term, "{codeperiexam}")
                variables["codeperiexam"] = str(code)
                break
                
        # 1. Détection des motifs connus
        for pattern, param_type in self.auto_patterns.items():
            matches = list(re.finditer(pattern, normalized))
            for match in reversed(matches):  # Traiter de droite à gauche
                full_match = match.group(0)
                
                if param_type == 'NomPrenom':
                    nom, prenom = match.groups()
                    normalized = normalized.replace(full_match, "{NomFr} {PrenomFr}")
                    variables.update({"NomFr": nom, "PrenomFr": prenom})
                else:
                    value = match.group(1) if len(match.groups()) > 0 else full_match
                    normalized = normalized.replace(full_match, f"{{{param_type}}}")
                    variables[param_type] = value

        # 2. Détection des valeurs entre quotes
        quoted_values = re.findall(r"['\"]([^'\"]+)['\"]", normalized)
        for val in quoted_values:
            if val not in variables.values():  
                if val.isupper() and len(val.split()) == 1:
                    param_name = "NomFr" if "nom" in normalized.lower() else "Valeur"
                    normalized = normalized.replace(f"'{val}'", f"'{{{param_name}}}'")
                    variables[param_name] = val

        return normalized, variables

    def _normalize_template(self, text: str) -> str:
        """Normalise le texte pour la comparaison de similarité"""
        normalized, _ = self._extract_parameters(text)
        # Supprime les espaces multiples et les caractères spéciaux
        normalized = re.sub(r'\s+', ' ', normalized).lower().strip()
        return normalized

    def find_similar_template(self, question: str, threshold: float = 0.85) -> Tuple[Optional[Dict], float]:
        """Trouve un template similaire en utilisant TF-IDF et cosine similarity"""
        if not self.cache:
            return None, 0.0
            
        norm_question = self._normalize_template(question)
        
        try:
            question_vec = self.vectorizer.transform([norm_question])
            similarities = cosine_similarity(question_vec, self.template_vectors)[0]
            best_idx = np.argmax(similarities)
            best_score = similarities[best_idx]
            
            if best_score >= threshold:
                cache_key = list(self.cache.keys())[best_idx]
                return self.cache[cache_key], best_score
        except Exception as e:
            print(f"⚠️ Erreur lors de la recherche de template similaire: {str(e)}")
        
        return None, 0.0

    def _generate_cache_key(self, question: str) -> str:
        """Génère une clé basée sur la question normalisée"""
        normalized_question, _ = self._extract_parameters(question)
        return hashlib.md5(normalized_question.encode('utf-8')).hexdigest()

    def _normalize_question(self, question: str) -> Tuple[str, Dict[str, str]]:
        """Alternative à extract_parameters pour compatibilité"""
        return self._extract_parameters(question)

    def _normalize_sql(self, sql: str, variables: Dict[str, str]) -> str:
        """Normalisation SQL avancée"""
        # Remplacer les IDs fixes par des placeholders
        sql = re.sub(
            r'(IdPersonne|e\.IdPersonne|eleve\.IdPersonne)\s+IN\s*\(\s*\d+\s*\)',
            r'\1 IN ({id_personne})',
            sql,
            flags=re.IGNORECASE
        )
        
        if "AnneeScolaire" in variables:
            value = variables["AnneeScolaire"]
            # Remplace toutes les variations possibles par la version avec guillemets
            for fmt in [value, f"'{value}'", f'"{value}"']:
                sql = sql.replace(fmt, "{AnneeScolaire}")
        
        if "codeperiexam" in variables:
            code = variables["codeperiexam"]
            sql = re.sub(r'codeperiexam\s*=\s*\d+', f'codeperiexam = {code}', sql)
            sql = re.sub(r"'?\d+'?\s*=\s*codeperiexam", f"'{code}' = codeperiexam", sql)
            
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'AND', 'OR']
        protected = []
        
        def protect(match):
            protected.append(match.group(0))
            return f"__PROTECTED_{len(protected)-1}__"
        
        temp_sql = re.sub('|'.join(keywords), protect, sql, flags=re.IGNORECASE)
        
        for param, value in variables.items():
            for fmt in [f"'{value}'", f'"{value}"', value]:
                if fmt in temp_sql:
                    temp_sql = temp_sql.replace(fmt, f"{{{param}}}")
        
        for i, kw in enumerate(protected):
            temp_sql = temp_sql.replace(f'__PROTECTED_{i}__', kw)
            
        return temp_sql



    def get_user_children_ids(self, user_id: int) -> List[int]:
        """Récupère les IDs des enfants d'un parent avec gestion robuste des connexions"""
        connection = None
        cursor = None
        children_ids = []

        try:
            query = """
            SELECT DISTINCT pe.id AS id_enfant
            FROM personne p
            JOIN parent pa ON p.id = pa.Personne
            JOIN parenteleve pev ON pa.id = pev.Parent
            JOIN eleve e ON pev.Eleve = e.id
            JOIN personne pe ON e.IdPersonne = pe.id
            WHERE p.id = %s
            """
            
            # Get connection
            connection = get_db()
            cursor = connection.cursor()
            
            # Execute query
            cursor.execute(query, (user_id,))
            users = cursor.fetchall()
            
            # Process results
            if users:
                children_ids = [user['id_enfant'] for user in users]
                logger.info(f"✅ Found {len(children_ids)} children for parent {user_id}")
            
            return children_ids
        except Exception as e:
            logger.error(f"❌ Error getting children for parent {user_id}: {str(e)}")
            logger.error(traceback.format_exc())
            return []
        finally:
            # Only close if we created a direct connection
            try:
                if cursor:
                    cursor.close()
                
                # Check if this is a Flask-managed connection
                from flask import current_app
                is_flask_connection = current_app and hasattr(current_app, 'extensions') and 'mysql' in current_app.extensions and connection == current_app.extensions['mysql'].connection
                
                if connection and not is_flask_connection:
                    connection.close()
                    logger.debug("🔌 Closed direct MySQL connection")
            except Exception as close_error:
                logger.warning(f"⚠️ Error during cleanup: {str(close_error)}")

    def cache_query(self, question: str, sql_query: str):
        """Version finale de mise en cache"""
        norm_question, vars_question = self._extract_parameters(question)
        norm_sql = self._normalize_sql(sql_query, vars_question)
        
        key = hashlib.md5(norm_question.encode()).hexdigest()
        self.cache[key] = {
            'question_template': norm_question,
            'sql_template': norm_sql
        }
        self._save_cache()

    def get_cached_query(self, question: str, current_user_id: int) -> Optional[Tuple[str, Dict[str, str]]]:
        """Version modifiée qui gère le remplacement direct de l'ID enfant dans le SQL"""
        
        normalized_question, variables = self._extract_parameters(question)
        key = self._generate_cache_key(normalized_question)
        
        if key in self.cache:
            cached = self.cache[key]
            sql_template = cached['sql_template']
            
            # Remplacer directement {id_personne} ou {{id_personne}} dans le SQL par les vrais IDs
            if '{id_personne}' in sql_template or '{{id_personne}}' in sql_template:
                children_ids = self.get_user_children_ids(current_user_id)
                if children_ids:
                    # Construire la valeur de remplacement selon le contexte
                    if len(children_ids) == 1:
                        id_replacement = str(children_ids[0])
                    else:
                        id_replacement = ','.join(str(id) for id in children_ids)
                    
                    # Remplacer les deux formats possibles
                    sql_template = sql_template.replace('{{id_personne}}', id_replacement)
                    sql_template = sql_template.replace('{id_personne}', id_replacement)
            
            # Gérer les autres variables normalement
            current_vars = {}
            for param in re.findall(r'\{(\w+)\}', sql_template):
                if param in variables:
                    current_vars[param] = variables[param]
            
            return sql_template, current_vars
        
        # Si pas de correspondance exacte, chercher un template similaire
        similar_template, score = self.find_similar_template(question)
        if similar_template:
            print(f"🔍 Template similaire trouvé (score: {score:.2f})")
            sql_template = similar_template['sql_template']
            
            # Remplacer directement {id_personne} ou {{id_personne}} dans le SQL par les vrais IDs
            if '{id_personne}' in sql_template or '{{id_personne}}' in sql_template:
                children_ids = self.get_user_children_ids(current_user_id)
                if children_ids:
                    # Construire la valeur de remplacement selon le contexte
                    if len(children_ids) == 1:
                        id_replacement = str(children_ids[0])
                    else:
                        id_replacement = ','.join(str(id) for id in children_ids)
                    
                    # Remplacer les deux formats possibles
                    sql_template = sql_template.replace('{{id_personne}}', id_replacement)
                    sql_template = sql_template.replace('{id_personne}', id_replacement)
            
            # Gérer les autres variables
            current_vars = {}
            for param in re.findall(r'\{(\w+)\}', sql_template):
                if param in variables:
                    current_vars[param] = variables[param]
                else:
                    # Essaye de trouver une valeur correspondante dans la question
                    for pattern in self.auto_patterns:
                        match = re.search(pattern, question)
                        if match:
                            value = match.group(1) if len(match.groups()) > 0 else match.group(0)
                            current_vars[param] = value
                            break
            
            return sql_template, current_vars
        
        return None
        
    def clean_double_braces_in_cache(self):
        """Nettoie le cache en remplaçant {{id_personne}} par {id_personne}"""
        updated = False
        
        for key, item in self.cache.items():
            sql_template = item.get("sql_template", "")
            if "{{id_personne}}" in sql_template:
                # Remplacer les doubles accolades par des simples
                item["sql_template"] = sql_template.replace("{{id_personne}}", "{id_personne}")
                updated = True
                logger.info(f"✅ Nettoyé les doubles accolades dans le template: {key}")
        
        if updated:
            self._save_cache()
            logger.info("✅ Cache nettoyé et sauvegardé")
        else:
            logger.info("ℹ️ Aucune double accolade trouvée dans le cache")