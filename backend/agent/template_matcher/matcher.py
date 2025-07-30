# import re
# import json
# import numpy as np
# from pathlib import Path
# from typing import List, Dict, Optional, Tuple
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity

# class SemanticTemplateMatcher:
#     def __init__(self):
#         self.vectorizer = TfidfVectorizer()
#         self.templates = []
#         self.template_vectors = None 

#     def load_templates(self, templates: List[Dict]) -> None:
#         if not templates:
#             raise ValueError("La liste de templates ne peut pas être vide")
        
#         # Filtrage des templates valides
#         valid_templates = []
#         template_texts = []
        
#         for t in templates:
#             if not isinstance(t, dict) or "template_question" not in t:
#                 continue
                
#             normalized = self._normalize_template(t["template_question"])
#             if normalized.strip():  
#                 valid_templates.append(t)
#                 template_texts.append(normalized)
        
#         if not valid_templates:
#             raise ValueError(
#                 "Aucun template valide après filtrage. "
#                 "Vérifiez que les templates contiennent bien 'template_question' "
#                 "et que le texte n'est pas vide après normalisation."
#             )
        
#         self.templates = valid_templates
#         self.template_vectors = self.vectorizer.fit_transform(template_texts)

#     def _normalize_template(self, text: str) -> str:
#         if not isinstance(text, str):
#             return ""
        
#         # Remplace les variables et normalise
#         text = re.sub(r'\{.+?\}', 'VAR', text)
#         text = text.lower().strip()
        
#         # Garde uniquement le texte significatif
#         return ' '.join([word for word in text.split() if len(word) > 1])
    
#     def find_similar_template(self, question: str, threshold: float = 0.8) -> Tuple[Optional[Dict], float]:
#         if not self.templates:
#             return None, 0.0
            
#         # Transforme la question en vecteur TF-IDF
#         question_vec = self.vectorizer.transform([self._normalize_template(question)])
        
#         # Calcul des similarités
#         similarities = cosine_similarity(question_vec, self.template_vectors)[0]
        
#         # Trouver le meilleur match
#         best_idx = np.argmax(similarities)
#         best_score = similarities[best_idx]
        
#         if best_score >= threshold:
#             return self.templates[best_idx], best_score
#         return None, 0.0


import re
from typing import Dict, List, Optional, Tuple

class SemanticTemplateMatcher:
    def __init__(self):
        self.templates = []
    
    def load_templates(self, templates: List[Dict]):
        """Charge les templates"""
        self.templates = templates
        print(f"✅ {len(templates)} templates chargés dans le matcher")
    
    def find_similar_template(self, question: str, threshold: float = 0.6) -> Tuple[Optional[Dict], float]:
        """Trouve un template similaire en utilisant une comparaison simple"""
        if not self.templates:
            return None, 0.0
        
        question_normalized = self._normalize_text(question)
        best_match = None
        best_score = 0.0
        
        for template in self.templates:
            template_text = template.get("template_question", "")
            template_normalized = self._normalize_text(template_text)
            
            # Calcul de similarité basé sur les mots communs
            similarity = self._calculate_similarity(question_normalized, template_normalized)
            
            if similarity > best_score and similarity >= threshold:
                best_score = similarity
                best_match = template
        
        return best_match, best_score
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour la comparaison"""
        # Supprime les placeholders
        text = re.sub(r'\{[^}]+\}', '', text)
        # Normalise les espaces et la casse
        text = re.sub(r'\s+', ' ', text.lower().strip())
        return text
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcule la similarité entre deux textes"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0