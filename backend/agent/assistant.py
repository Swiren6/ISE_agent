from config.database import get_db_connection,get_db
from langchain_community.utilities import SQLDatabase
from typing import List, Dict, Optional, Any, Tuple
from agent.llm_utils import ask_llm 
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv  
from agent.template_matcher.matcher import SemanticTemplateMatcher
import re
from pathlib import Path
from agent.cache_manager import CacheManager
from agent.sql_agent import SQLAgent
import json


load_dotenv()

# assistant.py - Corrections dans le PROMPT_TEMPLATE

PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["input", "table_info", "relevant_domain_descriptions", "relations"],
    template=f"""
[SYSTEM] Vous êtes un assistant SQL expert pour une base de données scolaire.
Votre rôle est de traduire des questions en français en requêtes SQL MySQL.

ATTENTION: 
***- Pour les absences : absence.Inscription = inscriptioneleve.id
***Pour lier élève et personne : eleve.IdPersonne = personne.id
**l'année scolaire se trouve dans anneescolaire.AnneeScolaire non pas dans Annee 
** si on dit l'annee XXXX/YYYY on parle de l'année scolaire XXXX/YYYY 
**les table eleve et parent ne contienne pas les noms et les prenoms . ils se trouvent dans la table personne.
**les table eleve et parent ne contienne pas les numéro de telephnone Tel1 et Tel2 . ils se trouvent dans la table personne.
**les colonnes principale  du table personne sont : id, NomFr, PrenomFr, NomAr , PrenomAr, Cin,AdresseFr, AdresseAr, Tel1, Tel2,Nationalite,Localite,Civilite.
**la trimestre 3 est d id 33, trimestre 2 est d id 32 , trimestre 1 est d id 31.

**CORRECTION IMPORTANTE POUR LES ABSENCES:**
**la table absence contient une colonne "Inscription" (pas "inscriptioneleve") qui fait référence à inscriptioneleve.id
**pour les absences d'un élève, faire: absence.Inscription = inscriptioneleve.id

**lorsque on veut avoir l id d un eleve  on fait cette jointure : 
id_inscription IN (
        SELECT id
        FROM inscriptioneleve
        WHERE Eleve IN (
            SELECT id
            FROM eleve
            WHERE IdPersonne = "numéro de id "
        )
**lorsque on veut savoir l id de la séance on fait la jointure suivante : s.id=e.SeanceDebut  avec s pour la seance et e pour Emploidutemps 
**lorsque on demande l etat de paiement on ne mais pas p.Annuler=0 avec p paiement ni CASE
        WHEN p.Annuler = 1 THEN 'Annulé'
        ELSE 'Actif'
    END AS statut_paiement.
**lorsque on veut savoir le paiement extra d un eleve on extrait le motif_paiement, le totalTTC  et le reste en faisant  la jointure entre le paiementextra et paiementextradetails d'une coté et paiementextra et paiementmotif d'une autre coté .
**lorsque on demande les détails de paiement scolaire on extrait le mode de reglement ,numéro de chèque , montant et la date de l'opération. 
**lorsque on demande l'mploi du temps d'un classe précie avec un jour précie on extrait le nom , le prénom de l'enseignant ,le nom de la matière , le nom de la salle , le debut et la fin de séance et le libelle de groupe (par classe...)
**Les coordonées de debut et de la fin de séance se trouve dans le table emploidutemps sous forme d'id ,les covertir en heures a l'aide de table seance . 
**la semaine A est d'id 2 , la semaine B est d'id 3 , Sans semaine d'id 1.
**les colonnes principale  du table personne sont : id, NomFr, PrenomFr, NomAr , PrenomAr, Cin,AdresseFr, AdresseAr, Tel1, Tel2,Nationalite,Localite,Civilite.
**pour les nom de jour en français on a une colone libelleJourFr avec mercredi c est ecrite Mercredi . 
**utiliser des JOINs explicites . exemple au lieu de :WHERE
    e.Classe = (SELECT id FROM classe WHERE CODECLASSEFR = '7B2')
    AND e.Jour = (SELECT id FROM jour WHERE libelleJourFr = 'Mercredi')
    ecrire:
 JOIN
     jour j ON e.Jour = j.id AND j.libelleJourFr = 'Mercredi'
JOIN
     classe c ON e.Classe = c.id AND c.CODECLASSEFR = '7B2'
**les résultats des trimestres se trouve dans le table Eduresultatcopie .
**l id de l eleve est liée par l id de la personne par Idpersonne 
**les eleves nouvellemmnent inscris ont un TypeInscri="N" et les eleves qui ont etudié auparavant a l'ecole ont TypeInscri="R".
**un éleves n'est pas réinscri est éleves qui est inscrits pendant l'année précédante et pas pour cette année . 
**la décision d'acceptation consernent seulement les nouveaux eleves inscrits a l'ecole.
**pour les cheques a echeance non valides consulter la table reglementeleve_echeancier .
**les cheques echancier non valide le champ isvalide=0.

Voici la structure détaillée des tables pertinentes pour votre tâche (nom des tables, colonnes et leurs types) :
{{table_info}}

---
**Description des domaines pertinents pour cette question :**
{{relevant_domain_descriptions}}

---
**Informations Clés et Relations Fréquemment Utilisées pour une meilleure performance :**
{{relations}}

---
**Instructions pour la génération SQL :**
1.  Répondez UNIQUEMENT par une requête SQL MySQL valide et correcte.
2.  Ne mettez AUCUN texte explicatif ou commentaire avant ou après la requête SQL. La réponse doit être purement la requête.
3.  **Sécurité :** Générez des requêtes `SELECT` uniquement. Ne générez **JAMAIS** de requêtes `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE` ou toute autre commande de modification/suppression de données.
4.  **Gestion de l'Année Scolaire :** Si l'utilisateur mentionne une année au format 'YYYY-YYYY' (ex: '2023-2024'), interprétez-la comme équivalente à 'YYYY/YYYY' et utilisez ce format pour la comparaison sur la colonne `Annee` de `anneescolaire` ou pour trouver l'ID correspondant.
5.  **Robustesse aux Erreurs et Synonymes :** Le modèle doit être tolérant aux petites fautes de frappe et aux variations de langage. Il doit s'efforcer de comprendre l'intention de l'utilisateur même si les termes ne correspondent pas exactement aux noms de colonnes ou de tables. Par exemple, "eleves" ou "étudiants" devraient être mappés à la table `eleve`. "Moyenne" ou "résultat" devraient faire référence à `dossierscolaire.moyenne_general` ou `edumoymati`.


Question : {{input}}
Requête SQL :
"""
)


class SQLAssistant:
        def __init__(self,db=None   ):
            self.db = db if db is not None else get_db_connection()
            self.sql_agent = SQLAgent(self.db)
            self.relations_description = self._safe_load_relations()
            self.domain_descriptions = self._safe_load_domain_descriptions()
            self.domain_to_tables_mapping = self._safe_load_domain_to_tables_mapping()
            self.ask_llm = ask_llm
            self.cache =CacheManager()
            self.template_matcher = SemanticTemplateMatcher()
            
            try:
                self.templates_questions = self.load_question_templates()
                if self.templates_questions:
                    print(f"✅ {len(self.templates_questions)} templates chargés")
                    self.template_matcher.load_templates(self.templates_questions)
                else:
                    print("⚠️ Aucun template valide - fonctionnement en mode LLM seul")
                    
            except ValueError as e:
                print(f"❌ Erreur de chargement des templates: {str(e)}")
                self.templates_questions = []

        def load_question_templates(self) -> list:
            print("🔍 Chargement des templates de questions...")
            try:
                # Chemin absolu plus fiable
                templates_path = Path(__file__).parent / 'templates_questions.json'
                
                # Vérification approfondie du fichier
                if not templates_path.exists():
                    print(f"⚠️ Fichier non trouvé, création: {templates_path}")
                    templates_path.write_text('{"questions": []}', encoding='utf-8')
                    return []

                content = templates_path.read_text(encoding='utf-8').strip()
                if not content:
                    print("⚠️ Fichier vide, réinitialisation")
                    templates_path.write_text('{"questions": []}', encoding='utf-8')
                    return []

                # Validation JSON stricte
                try:
                    data = json.loads(content)
                    if not isinstance(data.get("questions", []), list):
                        raise ValueError("Format invalide: 'questions' doit être une liste")
                    
                    # Validation de chaque template
                    valid_templates = []
                    for template in data["questions"]:
                        if all(key in template for key in ["template_question", "requete_template"]):
                            valid_templates.append(template)
                        else:
                            print(f"⚠️ Template incomplet ignoré: {template.get('description', 'sans description')}")
                    
                    return valid_templates

                except json.JSONDecodeError as e:
                    print(f"❌ Fichier JSON corrompu, réinitialisation. Erreur: {e}")
                    backup_path = templates_path.with_suffix('.bak.json')
                    templates_path.rename(backup_path)
                    templates_path.write_text('{"questions": []}', encoding='utf-8')
                    return []

            except Exception as e:
                print(f"❌ Erreur critique lors du chargement: {e}")
                return []
        
        def find_matching_template(self, question: str) -> Optional[Dict[str, Any]]:
            print(f"🔍 Recherche de template pour la question")
            exact_match = self._find_exact_template_match(question)
            if exact_match:
                return exact_match
            
            semantic_match, score = self.template_matcher.find_similar_template(question)
            if semantic_match:
                print(f"🔍 Template sémantiquement similaire trouvé (score: {score:.2f})")
                return self._extract_variables(question, semantic_match)
            
            return None

        def _find_exact_template_match(self, question: str) -> Optional[Dict[str, Any]]:
            cleaned_question = question.rstrip(' ?')
            for template in self.templates_questions:
                pattern = template["template_question"]
                regex_pattern = re.sub(r'\{(.+?)\}', r'(?P<\1>.+?)', pattern)
                match = re.fullmatch(regex_pattern, cleaned_question, re.IGNORECASE)
                if match:
                    variables = {k: v.strip() for k, v in match.groupdict().items()}
                    return {
                        "template": template,
                        "variables": variables if variables else {}
                    }
            return None
        
        def _extract_variables(self, question: str, template: Dict) -> Dict[str, Any]:
            template_text = template["template_question"]
            variables = {}

            annee_pattern = r"(20\d{2}[-\/]20\d{2})"
            annee_match = re.search(annee_pattern, question)
            if annee_match:
                variables["AnneeScolaire"] = annee_match.group(1).replace("-", "/")
            
            var_names = re.findall(r'\{(.+?)\}', template_text)
            for var_name in var_names:
                if var_name not in variables:  
                    keyword_pattern = re.escape(template_text.split(f"{{{var_name}}}")[0].split()[-1])
                    pattern = fr"{keyword_pattern}\s+([^\s]+)"
                    match = re.search(pattern, question, re.IGNORECASE)
                    if match:
                        variables[var_name] = match.group(1).strip(",.?!")
            
            return {
                "template": template,
                "variables": variables if variables else {}
            }

        def generate_query_from_template(self, template: Dict, variables: Dict) -> str:
            requete = template["requete_template"]
            if not variables:
                return requete
            
            for var_name, var_value in variables.items():
                clean_value = str(var_value).split('?')[0].strip(",.!?\"'")
                
                if var_name.lower() == "anneescolaire":
                    clean_value = clean_value.replace("-", "/")
                
                requete = requete.replace(f'{{{var_name}}}', clean_value)
            
            return requete
        
        def _filter_table_columns(self, table_block: str, question: str) -> str:
            lines = table_block.split('\n')
            if not lines:  # ← Ajouter cette vérification
                return table_block
                
            filtered_lines = [lines[0]]  
            
            for line in lines[1:]:
                if any(keyword.lower() in line.lower() for keyword in ['nom', 'prenom', 'date', 'absence']):
                    filtered_lines.append(line)
            
            return '\n'.join(filtered_lines) 

        def get_relevant_domains(self, query: str, domain_descriptions: Dict[str, str]) -> List[str]:
            """Identifies relevant domains based on a user query using DeepSeek."""
            domain_desc_str = "\n".join([f"- {name}: {desc}" for name, desc in domain_descriptions.items()])
            domain_prompt_content = f"""
            Based on the following user question, identify ALL relevant domains from the list below.
            Return only the names of the relevant domains, separated by commas. If no domain is relevant, return 'None'.

            User Question: {query}

            Available Domains and Descriptions:
            {domain_desc_str}

            Relevant Domains (comma-separated):
            """
            
            try:
                response = self.ask_llm(domain_prompt_content)
                domain_names = response.strip()
                
                if domain_names.lower() == 'none' or not domain_names:
                    return []
                return [d.strip() for d in domain_names.split(',')]
            except Exception as e:
                print(f"❌ Erreur lors de l'identification des domaines: {e}")
                return []
        
        
        def _format_tabular_result(self, headers: list, rows: list, question: str = "") -> str:
            """Formate les résultats sous forme de tableau"""
            output = [f"**{question}**"] if question else []
            output.append(" | ".join(headers))
            output.append("-+-".join(['-' * len(h) for h in headers]))
            for row in rows:
                output.append(" | ".join(row))
            return "\n".join(output) 
        def _format_string_result(self, result_str: str, question: str = "") -> str:
            """Formate un résultat de type string retourné par db.run()"""
            if not result_str.strip():
                return "✅ Requête exécutée mais aucun résultat trouvé."
            
            # Si c'est un résultat simple (nombre, etc.)
            lines = result_str.strip().split('\n')
            if len(lines) == 1:
                return f"Résultat : {lines[0]}"
            
            # Si c'est un tableau de résultats
            output = [f"**{question}**"] if question else []
            output.extend(lines)
            return "\n".join(output)
        
        def get_tables_from_domains(self, domains: List[str], domain_to_tables_map: Dict[str, List[str]]) -> List[str]:
            """Retrieves all tables associated with the given domains."""
            tables = []
            for domain in domains:
                tables.extend(domain_to_tables_map.get(domain, []))
            return sorted(list(set(tables)))
    
                
        def debug_table_info(self, tables=None):
            """Debug pour voir exactement ce que retourne get_table_info"""
            try:
                if tables:
                    table_info = self.db.get_table_info(table_names=tables)
                else:
                    table_info = self.db.get_table_info()
                
                print("="*50)
                print("DEBUG TABLE INFO:")
                print("="*50)
                print(table_info)
                print("="*50)
                return table_info
            except Exception as e:
                print(f"❌ Erreur debug_table_info: {e}")
                return "Erreur debug"
            
        def _safe_load_relations(self) -> str:
            """Charge les relations avec gestion d'erreurs"""
            try:
                relations_path = Path(__file__).parent / 'prompts' / 'relations.txt'  
                print(f"🔍 Tentative de chargement depuis : {relations_path.absolute()}")# Log du chemin

                          
                if relations_path.exists():
                    content = relations_path.read_text(encoding='utf-8')
                    print(f"✅ Contenu chargé (premières 50 lignes) :\n{content[:500]}...")  # Aperçu du contenu
                    return content
                else:
                    print("⚠️ Fichier relations.txt non trouvé")
                    return "# Aucune relation définie"
                    
            except Exception as e:
                print(f"❌ Erreur lors du chargement : {str(e)}")
                return "# Erreur chargement relations"
                
        def _safe_load_domain_descriptions(self) -> dict:
            """Charge les descriptions de domaine avec gestion d'erreurs"""
            try:
                domain_path = Path(__file__).parent / 'prompts' / 'domain_descriptions.json'
                if domain_path.exists():
                    with open(domain_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                print("⚠️ Fichier domain_descriptions.json non trouvé")
                return {}
            except Exception as e:
                print(f"❌ Erreur chargement domain descriptions: {e}")
                return {}
        
        def _safe_load_domain_to_tables_mapping(self) -> dict:
            """Charge le mapping domaine-tables avec gestion d'erreurs"""
            try:
                mapping_path = Path(__file__).parent / 'prompts' / 'domain_tables_mapping.json'
                if mapping_path.exists():
                    with open(mapping_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                print("⚠️ Fichier domain_tables_mapping.json non trouvé")
                return {}
            except Exception as e:
                print(f"❌ Erreur chargement domain mapping: {e}")
                return {}
        
        def _safe_load_question_templates(self) -> list:
            """Charge les templates avec gestion d'erreurs robuste"""
            try:
                templates_path = Path(__file__).parent / 'templates_questions.json'
                
                if not templates_path.exists():
                    print(f"⚠️ Création fichier templates: {templates_path}")
                    templates_path.write_text('{"questions": []}', encoding='utf-8')
                    return []

                content = templates_path.read_text(encoding='utf-8').strip()
                if not content:
                    return []

                data = json.loads(content)
                if not isinstance(data.get("questions", []), list):
                    return []
                
                valid_templates = []
                for template in data["questions"]:
                    if all(key in template for key in ["template_question", "requete_template"]):
                        valid_templates.append(template)
                
                return valid_templates

            except Exception as e:
                print(f"❌ Erreur chargement templates: {e}")
                return []

        def get_student_info_by_name(self, full_name):
            """Récupère les infos d'un élève depuis la base de données"""
            return self.sql_agent.get_student_info_by_name(full_name)

        def _trim_history(self):
            while self.conversation_history and sum(msg['tokens'] for msg in self.conversation_history) > self.max_history_tokens:
                self.conversation_history.pop(0)

        def _build_response(self, response, sql_query=None, db_results=None, tokens=0, cost=0):
            return {
                "response": response,
                "sql_query": sql_query,
                "db_results": db_results,
                "tokens_used": tokens,
                "estimated_cost_usd": cost,
                "conversation_id": id(self.conversation_history)
            }

        def ask_question(self, question: str) -> Tuple[str, str]:
            # 1. Vérifier le cache
            cached_response = self.cache.get_cached_query(question)
            if cached_response:
                logger.info("Cache hit!")
                sql_query = cached_response['sql_query']
                formatted_result = cached_response['result']
                return sql_query, formatted_result

            # 2. Tenter de faire correspondre un template sémantique
            template_match = self.find_matching_template(question)
            template_match = self.find_matching_template(question)
    
            if template_match:
                sql_query = self.generate_query_from_template(
                    template_match["template"],
                    template_match.get("variables", {})
                )
                logger.info(f"Template match: {sql_query}")
                
                try:
                    conn = get_db()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute(sql_query)
                    
                    result = cursor.fetchall()
                    cursor.close()
                    if hasattr(conn, '_direct_connection'):
                        conn.close()

                    formatted_result = self.format_sql_result(result, question)
                    self.cache.cache_query(question, sql_query)
                    
                    return sql_query, formatted_result
                    
                except Exception as db_error:
                    error_msg = str(db_error)
                    logger.error(f"Erreur d'exécution SQL (template): {error_msg}")
                    return sql_query, f"❌ Erreur d'exécution SQL (template) : {error_msg}"
                    # 3. Si aucun template ne correspond, utiliser le LLM
            else:
                logger.info("No template match, using LLM.")
                table_info = self.db.get_table_info_as_str()
                
                relevant_tables_from_question = re.findall(r'\b(eleve|enseignant|matiere|note|absence|personnel|inscriptioneleve|parent|niveau|personne|salle|niveauetude|typepersonnel|cycleetude|section|semainematiere|annee_scolaire)\b', question, re.IGNORECASE)
                relevant_tables_info = []
                relevant_domains = set()

                for table_name in set(relevant_tables_from_question):
                    table_schema = self.db.get_table_info_as_str([table_name])
                    if table_schema:
                        relevant_tables_info.append(table_schema)
                        if table_name.lower() in self.domain_descriptions:
                            relevant_domains.add(self.domain_descriptions[table_name.lower()])
                
                # If no specific tables are mentioned, provide schema for common tables
                if not relevant_tables_info:
                    logger.info("No specific tables found in question, using common tables.")
                    common_tables = ['eleve', 'personne', 'inscriptioneleve', 'absence', 'note', 'matiere', 'enseignant', 'niveau']
                    for table_name in common_tables:
                        table_schema = self.db.get_table_info_as_str([table_name])
                        if table_schema:
                            relevant_tables_info.append(table_schema)
                            if table_name.lower() in self.domain_descriptions:
                                relevant_domains.add(self.domain_descriptions[table_name.lower()])

                filtered_blocks = [self._filter_table_columns(block, question) for block in relevant_tables_info]
                filtered_blocks = [block for block in filtered_blocks if block.strip()] # Remove empty blocks
                
                domain_desc = ", ".join(sorted(list(relevant_domains))) if relevant_domains else "informations générales sur la base de données scolaire."

                prompt = PROMPT_TEMPLATE.format(
                    input=question,
                    table_info="\n\n".join(filtered_blocks),
                    relevant_domain_descriptions=domain_desc,
                    relations=self.relations_description
                )

                llm_response = self.ask_llm(prompt)
                sql_query = llm_response.replace("```sql", "").replace("```", "").strip()
                
                if not sql_query:
                    return "", "❌ La requête générée est vide."

                # Exécution de la requête
                try:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute(sql_query)
                    
                    # Fetch results directly as DictCursor is configured
                    result = cursor.fetchall()
                    
                    cursor.close()
                    if hasattr(conn, '_direct_connection'):
                        conn.close()

                    formatted_result = self.format_sql_result(result, question)
                    self.cache.cache_query(question, sql_query)
                    
                    attestation = self.generate_attestation(sql_query, formatted_result)
                    if attestation:
                        formatted_result += f"\n\n{attestation}"

                    return sql_query, formatted_result
                    
                except Exception as db_error:
                    error_msg = str(db_error)
                    logger.error(f"Erreur d'exécution SQL : {error_msg}")
                    return sql_query, f"❌ Erreur d'exécution SQL : {error_msg}"

        
        def format_structured_result(self, result: Any, question: str = "") -> str:
            """Formate les résultats SQL de manière structurée"""
            # ✅ Réutiliser la même logique que format_sql_result
            return self.format_sql_result(result, question)

        def get_response(self, user_query, user_id=None):
            if user_id:
                print(f"🔐 Utilisateur connecté : {user_id}")
            # ✨ Détection demande d'attestation
            if "attestation de présence" in user_query.lower():
                from pdf_utils.attestation import export_attestation_pdf

                # 👉 Tu peux rendre ça dynamique plus tard
                donnees_etudiant = {
                    "nom": "Rania Zahraoui",
                    "date_naissance": "15/03/2005",
                    "matricule": "2023A0512",
                    "etablissement": "Lycée Pilote de Sfax",
                    "classe": "3ème Sciences",
                    "annee_scolaire": "2024/2025",
                    "lieu": "Sfax"
                }

                pdf_path = export_attestation_pdf(donnees_etudiant)
                return {
                    "response": f"L'attestation a été générée : <a href='/{pdf_path.replace(os.sep, '/')}' download>Télécharger le PDF</a>"
                }

            try:
                # Utilisation de la logique SQL existante
                sql_query, formatted_result = self.ask_question(user_query)
                
                # Generate natural language response using LLM
                if formatted_result and not formatted_result.startswith("❌"):
                    prompt = f"""
                    Question de l'utilisateur: {user_query}
                    Requête SQL générée: {sql_query}
                    Résultats: {formatted_result[:1000]}
                    
                    Tu es un assistant pédagogique. Reformule ces résultats SQL bruts en réponse naturelle, utile et claire en français.
                    """
                    
                    try:
                        natural_response = self.ask_llm(prompt)
                        return {
                            "response": natural_response,
                            "sql_query": sql_query,
                            "raw_results": formatted_result
                        }
                    except Exception as llm_error:
                        # Fallback: retourner le résultat formaté si LLM échoue
                        return {
                            "response": formatted_result,
                            "sql_query": sql_query,
                            "raw_results": formatted_result,
                            "llm_error": str(llm_error)
                        }
                else:
                    return {
                        "response": formatted_result or "Aucun résultat trouvé.",
                        "sql_query": sql_query
                    }
                    
            except Exception as e:
                return {
                    "response": f"Désolé, une erreur s'est produite: {str(e)}",
                    "sql_query": None,
                    "error": str(e)
                }
                
        def format_sql_result(self, result: Any, question: str = "") -> str:
            """Formate les résultats SQL de manière robuste"""
            if not result:
                return "✅ Requête exécutée mais aucun résultat trouvé."

            try:
                # Cas 1: Résultat est déjà une string
                if isinstance(result, str):
                    return self._format_string_result(result, question)
                
                # Cas 2: Résultat est un dictionnaire (pour COUNT, SUM etc.)
                if isinstance(result, dict):
                    return "\n".join([f"{k}: {v}" for k, v in result.items()])
                
                # Cas 3: Résultat est une liste
                if isinstance(result, list):
                    if not result:
                        return "✅ Requête exécutée mais aucun résultat trouvé."
                        
                    # Cas 3.1: Liste de dictionnaires
                    if isinstance(result[0], dict):
                        headers = list(result[0].keys())
                        rows = [[str(row.get(h, '')) for h in headers] for row in result]
                        return self._format_tabular_result(headers, rows, question)
                    
                    # Cas 3.2: Liste de tuples/listes
                    elif isinstance(result[0], (tuple, list)):
                        if cursor := getattr(self.db, '_last_cursor', None):
                            headers = [desc[0] for desc in cursor.description]
                        else:
                            headers = [f"Colonne_{i+1}" for i in range(len(result[0]))]
                        
                        rows = [[str(cell) for cell in row] for row in result]
                        return self._format_tabular_result(headers, rows, question)
                
                # Cas par défaut
                return f"Résultat : {str(result)}"
            
            except Exception as e:
                return f"❌ Erreur de formatage : {str(e)}\nRésultat brut: {str(result)[:500]}"       
        
            """Traite une question et retourne la requête SQL et la réponse formatée"""
            # 1. Vérification du cache
            cached = self.cache.get_cached_query(question)
            if cached:
                sql_template, variables = cached
                sql_query = sql_template
                for column, value in variables.items():
                    sql_query = sql_query.replace(f"{{{column}}}", value)
                
                print("⚡ Requête récupérée depuis le cache")
                try:
                    conn = get_db()
                    cursor = conn.cursor()  # Retrait de dictionary=True
                    cursor.execute(sql_query)
                    
                    # Récupération manuelle des résultats sous forme de dict
                    columns = [col[0] for col in cursor.description]
                    result = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    
                    cursor.close()
                    if hasattr(conn, '_direct_connection'):
                        conn.close()
                    
                    return sql_query, self.format_sql_result(result, question)
                except Exception as db_error:
                    return sql_query, f"❌ Erreur d'exécution SQL : {str(db_error)}"

            # 2. Vérification des templates
            template_match = self.find_matching_template(question)
            if template_match:
                print("🔍 Utilisation d'un template pré-enregistré")
                sql_query = self.generate_query_from_template(
                    template_match["template"],
                    template_match["variables"]
                )
                
                try:
                    conn = get_db()
                    cursor = conn.cursor()  # Retrait de dictionary=True
                    cursor.execute(sql_query)
                    
                    # Conversion manuelle en dictionnaire
                    columns = [col[0] for col in cursor.description]
                    result = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    
                    cursor.close()
                    if hasattr(conn, '_direct_connection'):
                        conn.close()
                    
                    formatted_result = self.format_sql_result(result, question)
                    self.cache.cache_query(question, sql_query)
                    return sql_query, formatted_result
                except Exception as db_error:
                    return sql_query, f"❌ Erreur d'exécution SQL : {str(db_error)}"

            # 3. Génération via LLM (reste identique)
            print("🔍 Génération via LLM")
            if not self.db:
                raise RuntimeError("Connexion DB non initialisée")

            relevant_domains = self.get_relevant_domains(question, self.domain_descriptions)
            tables = self.get_tables_from_domains(relevant_domains, self.domain_to_tables_mapping)
            
            all_table_info = self.db.get_table_info() 
            filtered_blocks = [
                block for block in all_table_info.split('\n\n') 
                if any(table in block.split('\n')[0] for table in tables)
            ]

            domain_desc = "\n".join([
                f"{d}: {self.domain_descriptions.get(d, '')}" 
                for d in relevant_domains
            ])

            prompt = PROMPT_TEMPLATE.format(
                input=question,
                table_info="\n\n".join(filtered_blocks),
                relevant_domain_descriptions=domain_desc,
                relations=self.relations_description
            )

            llm_response = self.ask_llm(prompt)
            sql_query = llm_response.replace("```sql", "").replace("```", "").strip()
            
            if not sql_query:
                return "", "❌ La requête générée est vide."

            # Exécution de la requête
            try:
                conn = get_db()
                cursor = conn.cursor()  # Retrait de dictionary=True
                cursor.execute(sql_query)
                
                # Conversion manuelle en dictionnaire
                columns = [col[0] for col in cursor.description]
                result = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                cursor.close()
                if hasattr(conn, '_direct_connection'):
                    conn.close()

                formatted_result = self.format_sql_result(result, question)
                self.cache.cache_query(question, sql_query)
                
                return sql_query, formatted_result
                
            except Exception as db_error:
                error_msg = str(db_error)
                return sql_query, f"❌ Erreur d'exécution SQL : {error_msg}"