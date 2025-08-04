import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import hashlib
import re
from collections import defaultdict

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    np = None
    SKLEARN_AVAILABLE = False
    print("⚠️ sklearn non disponible - utilisation de la comparaison simple")

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
        self.vectorizer = self.TfidfVectorizer()
        self.template_vectors = None
        self._init_similarity_search()
        if self.SKLEARN_AVAILABLE:
            self.vectorizer = self.TfidfVectorizer()
            self.template_vectors = None
            self._init_similarity_search()
        else:
            self.vectorizer = None
            self.template_vectors = None

    def _init_similarity_search(self):
        """Initialise le système de recherche de similarité"""
        if not self.SKLEARN_AVAILABLE or not self.cache:
            return
            
        templates = [self._normalize_template(item['question_template']) 
                    for item in self.cache.values()]
        self.vectorizer.fit(templates)
        self.template_vectors = self.vectorizer.transform(templates)

    def find_similar_template(self, question: str, threshold: float = 0.85) -> Tuple[Optional[Dict], float]:
        """Trouve un template similaire"""
        if not self.cache:
            return None, 0.0
        
        if self.SKLEARN_AVAILABLE and self.template_vectors is not None:
            # Utiliser sklearn si disponible
            norm_question = self._normalize_template(question)
            try:
                question_vec = self.vectorizer.transform([norm_question])
                similarities = self.cosine_similarity(question_vec, self.template_vectors)[0]
                best_idx = np.argmax(similarities)
                best_score = similarities[best_idx]
                
                if best_score >= threshold:
                    cache_key = list(self.cache.keys())[best_idx]
                    return self.cache[cache_key], best_score
            except Exception as e:
                print(f"⚠️ Erreur sklearn: {str(e)}")
        
        # Fallback : comparaison simple
        return self._simple_similarity_search(question, threshold)

    def _simple_similarity_search(self, question: str, threshold: float = 0.8) -> Tuple[Optional[Dict], float]:
        """Comparaison de similarité simple sans sklearn"""
        norm_question = self._normalize_template(question)
        best_match = None
        best_score = 0.0
        
        for cache_key, cached_item in self.cache.items():
            norm_template = self._normalize_template(cached_item['question_template'])
            
            # Calcul de similarité simple basé sur les mots communs
            question_words = set(norm_question.split())
            template_words = set(norm_template.split())
            
            if not question_words or not template_words:
                continue
                
            intersection = question_words.intersection(template_words)
            union = question_words.union(template_words)
            
            similarity = len(intersection) / len(union) if union else 0.0
            
            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = cached_item
        
        return best_match, best_score    
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
                r'\b(?:mon|ma|mes)\s+(enfant|fille|fils|enfants)\b': 'mon_enfant',
                r'\b(?:de|du|d\')\s*(?:mon|ma|mes)\s+(enfant|fille|fils|enfants)\b': 'mon_enfant',
                r'\bmon\s+enfant\b': 'mon_enfant',
                r'\bma\s+fille\b': 'mon_enfant', 
                r'\bmon\s+fils\b': 'mon_enfant',
                r'\bmes\s+enfants\b': 'mon_enfant'
            }
            
            family_refs = {}
            normalized_question = question.lower()
            
            for pattern, placeholder in family_patterns.items():
                if re.search(pattern, normalized_question, re.IGNORECASE):
                    family_refs['family_relation'] = 'mon_enfant'
                    break

    def _normalize_sql_for_family(self, sql_query: str, children_ids: List[int]) -> str:
            """Normalise le SQL en remplaçant les IDs enfants par des placeholders"""
            normalized_sql = sql_query

            children_ids_str = [str(id) for id in children_ids]

            joined_ids_regex = '|'.join(children_ids_str)
            joined_ids_in_clause = ',\\s*'.join(children_ids_str)

            patterns_to_replace = [
                (rf"IdPersonne\s*=\s*({joined_ids_regex})", "IdPersonne = {child_id}"),
                (rf"e\.IdPersonne\s*=\s*({joined_ids_regex})", "e.IdPersonne = {child_id}"),
                (rf"eleve\.IdPersonne\s*=\s*({joined_ids_regex})", "eleve.IdPersonne = {child_id}"),
                (rf"IdPersonne\s+IN\s*\(\s*({joined_ids_in_clause})\s*\)", "IdPersonne IN ({child_id})"),
                (rf"e\.IdPersonne\s+IN\s*\(\s*({joined_ids_in_clause})\s*\)", "e.IdPersonne IN ({child_id})"),
                (rf"WHERE\s+IdPersonne\s+IN\s*\(\s*({joined_ids_regex})\s*\)", "WHERE IdPersonne IN ({child_id})")
            ]

            for pattern, replacement in patterns_to_replace:
                normalized_sql = re.sub(pattern, replacement, normalized_sql, flags=re.IGNORECASE)

            return normalized_sql

    def _extract_parameters(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Détection intelligente des paramètres"""
        variables = {}
        normalized = text

        normalized, variables = self._handle_family_references(normalized, variables)
        normalized, variables = self._handle_trimestre_mapping(normalized, variables)
        normalized, variables = self._handle_auto_patterns(normalized, variables)
        normalized, variables = self._handle_quoted_values(normalized, variables)

        return normalized, variables

    def _handle_family_references(self, text: str, variables: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
        family_refs = self._extract_family_references(text)
        normalized = text
        if family_refs:
            family_patterns = [
                r'\b(?:mon|ma|mes)\s+(?:enfant|fille|fils|enfants)\b',
                r'\b(?:de|du|d\')\s*(?:mon|ma|mes)\s+(?:enfant|fille|fils|enfants)\b'
            ]
            for pattern in family_patterns:
                normalized = re.sub(pattern, '{family_relation}', normalized, flags=re.IGNORECASE)
            variables['family_relation'] = 'mon_enfant'
        return normalized, variables

    def _handle_trimestre_mapping(self, text: str, variables: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
        normalized = text
        for term, code in self.trimestre_mapping.items():
            if term in normalized.lower():
                normalized = normalized.replace(term, "{codeperiexam}")
                variables["codeperiexam"] = str(code)
                break
        return normalized, variables

    def _handle_auto_patterns(self, text: str, variables: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
        normalized = text
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
        return normalized, variables

    def _handle_quoted_values(self, text: str, variables: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
        normalized = text
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

    def _generate_cache_key(self, question: str) -> str:
            """Génère une clé basée sur la question normalisée"""
            normalized_question, _ = self._extract_parameters(question)
            return hashlib.md5(normalized_question.encode('utf-8')).hexdigest()

    def _normalize_question(self, question: str) -> Tuple[str, Dict[str, str]]:
            """Alternative à extract_parameters pour compatibilité"""
            return self._extract_parameters(question)

    def _normalize_sql(self, sql: str, variables: Dict[str, str]) -> str:
            """Normalisation SQL avancée"""
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

    def get_cached_query(self, question: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """Version compatible avec la détection automatique"""
        normalized_question, variables = self._extract_parameters(question)
        key = self._generate_cache_key(normalized_question)

        # Try exact match
        result = self._get_exact_match(key, variables)
        if result:
            return result

        # Try similar template match
        result = self._get_similar_match(question, variables)
        if result:
            return result

        return None

    def _get_exact_match(self, key: str, variables: Dict[str, str]) -> Optional[Tuple[str, Dict[str, str]]]:
        if key in self.cache:
            cached = self.cache[key]
            current_vars = self._extract_template_variables(cached['sql_template'], variables)
            return cached['sql_template'], current_vars
        return None

    def _get_similar_match(self, question: str, variables: Dict[str, str]) -> Optional[Tuple[str, Dict[str, str]]]:
        similar_template, score = self.find_similar_template(question)
        if similar_template:
            print(f"🔍 Template similaire trouvé (score: {score:.2f})")
            current_vars = self._extract_template_variables(similar_template['sql_template'], variables, question)
            return similar_template['sql_template'], current_vars
        return None

    def _extract_template_variables(self, sql_template: str, variables: Dict[str, str], question: Optional[str] = None) -> Dict[str, str]:
        current_vars = {}
        params = re.findall(r'\{(\w+)\}', sql_template)
        for param in params:
            if param in variables:
                current_vars[param] = variables[param]
            elif question is not None:
                value = self._find_param_in_question(param, question)
                if value is not None:
                    current_vars[param] = value
        return current_vars

    def _find_param_in_question(self, param: str, question: str) -> Optional[str]:
        """Helper to extract a parameter value from the question using auto_patterns."""
        for pattern in self.auto_patterns:
            match = re.search(pattern, question)
            if match:
                return match.group(1) if len(match.groups()) > 0 else match.group(0)
        return None

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
