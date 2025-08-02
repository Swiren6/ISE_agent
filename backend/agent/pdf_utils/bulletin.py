from fpdf import FPDF
from datetime import datetime
from pathlib import Path
import arabic_reshaper
from bidi.algorithm import get_display
import logging
from typing import Dict, List, Any, Optional, Union
from config.database import get_db
import os
import re

logger = logging.getLogger(__name__)

class BulletinPDFGenerator:
    """Générateur de bulletins scolaires dynamiques avec gestion automatique des périodes"""
    
    def __init__(self):
        self.font_dir = Path(r"C:\Users\HP\Desktop\assistant_ISE - Copie\backend\agent\pdf_utils\fonts\Amiri")
        self.output_dir = Path(__file__).parent.parent.parent / "static" / "bulletins"
        self._validate_resources()
    
    TRIMESTRE_MAP = {
        "premier trimestre": 31,
        "1er trimestre": 31,
        "1ère trimestre": 31,
        "deuxième trimestre": 32,
        "2ème trimestre": 32,
        "troisième trimestre": 33,
        "3ème trimestre": 33
    }
    
    @staticmethod
    def determine_annee_scolaire(date_reference: datetime = None) -> str:
        """Détermine l'année scolaire en cours automatiquement"""
        date_ref = date_reference or datetime.now()
        annee_debut = date_ref.year if date_ref.month >= 9 else date_ref.year - 1
        return f"{annee_debut}/{annee_debut + 1}"
    
    @staticmethod
    def parse_question(question: str) -> Dict[str, Any]:
        """Analyse la question pour extraire les paramètres de recherche"""
        question = question.lower().strip()
        
        # Détection du trimestre
        trimestre_id = None
        for label, id_trim in BulletinPDFGenerator.TRIMESTRE_MAP.items():
            if label in question:
                trimestre_id = id_trim
                question = question.replace(label, "")
                break
        
        # Nettoyage du nom
        question = re.sub(r"(donne moi|bulletin de|pour|le|la)", "", question)
        nom_clean = question.strip()
        
        return {
            "nom": nom_clean,
            "trimestre_id": trimestre_id
        }

    def _validate_resources(self):
        """Vérifie que les ressources nécessaires sont disponibles"""
        if not self.font_dir.exists():
            raise FileNotFoundError(f"Dossier des polices introuvable: {self.font_dir}")
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True)

    def _render_arabic(self, text: str) -> str:
        """Traite le texte arabe pour l'affichage"""
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            return get_display(reshaped_text)
        except Exception as e:
            logger.error(f"Erreur rendu arabe: {e}")
            return text

    def get_student_data_from_db(self, student_id: int, trimestre_id: Optional[int] = None, 
                           annee_scolaire: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        annee_scolaire = annee_scolaire or self.determine_annee_scolaire()
        trimestres = [trimestre_id] if trimestre_id else [31, 32, 33]
        
        conn = None
        cursor = None
        
        try:
            conn = get_db()
            cursor = conn.cursor(dictionary=True)
            
            # 1. Requête élève avec vérification de l'ID service
            student_query = """
            SELECT 
                p.NomFr, p.PrenomFr,
                CONCAT(p.NomFr, ' ', p.PrenomFr) AS nom_complet,
                e.DateNaissance, e.LieuNaissance, e.AutreLieuNaissance,
                c.CODECLASSEFR as classe, n.NOMNIVAR as niveau,
                e.id as eleve_id, e.IdPersonne as matricule, 
                e.idedusrv as id_service,
                ie.id as inscription_id
            FROM eleve e
            JOIN personne p ON e.IdPersonne = p.id
            JOIN inscriptioneleve ie ON e.id = ie.Eleve
            JOIN classe c ON ie.Classe = c.id
            JOIN niveau n ON c.IDNIV = n.id
            JOIN anneescolaire a ON ie.AnneeScolaire = a.id
            WHERE e.IdPersonne = %s AND a.AnneeScolaire = %s
            LIMIT 1
            """
            cursor.execute(student_query, (student_id, annee_scolaire))
            student_info = cursor.fetchone()
            
            if not student_info:
                logger.error(f"Élève {student_id} non trouvé pour {annee_scolaire}")
                return None
                
            if not student_info.get('id_service'):
                logger.error(f"Aucun ID service trouvé pour l'élève {student_id}")
                return None

            # 2. Recherche des notes par trimestre
            results = []
            for trim_id in trimestres:
                notes_query = """
                SELECT 
                    em.libematifr AS matiere,
                    CAST(ed.moyemati AS DECIMAL(5,2)) AS moyenne,
                    4 as coefficient
                FROM Edumoymaticopie ed
                JOIN Edumatiere em ON ed.codemati = em.codemati
                WHERE ed.idenelev = %s
                    AND ed.codeperiexam = %s
                    AND ed.moyemati IS NOT NULL
                    AND ed.moyemati != '0.00'
                """
                cursor.execute(notes_query, (student_info['id_service'], trim_id))
                notes_data = cursor.fetchall()
                
                if not notes_data:
                    logger.warning(f"Aucune note trouvée pour {student_id} (Trimestre {trim_id})")
                    continue
                    
                # Traitement des notes...
                total_points = 0
                total_coeff = 0
                matieres = []
                
                for note in notes_data:
                    moyenne = float(note['moyenne'])
                    coeff = int(note['coefficient'])
                    
                    total_points += moyenne * coeff
                    total_coeff += coeff
                    
                    matieres.append({
                        'nom': note['matiere'],
                        'coefficient': coeff,
                        'moyenne': moyenne,
                        'appreciation': self._get_appreciation(moyenne)
                    })
                
                # Calcul moyenne générale
                moy_gen = round(total_points / total_coeff, 2) if total_coeff > 0 else 0
                
                results.append({
                    'student_data': {
                        **student_info,
                        'nom': student_info['nom_complet'],
                        'periode': self._get_period_name(trim_id, annee_scolaire),
                        'moyenne_generale': moy_gen,
                        'rang': self._get_student_ranking(cursor, student_info['inscription_id'], trim_id, moy_gen),
                        'mention': self._get_appreciation(moy_gen),
                        'trimestre_id': trim_id
                    },
                    'matieres': matieres
                })
            
            return results[0] if trimestre_id and results else results
            
        except Exception as e:
            logger.error(f"Erreur base de données: {str(e)}")
            return None
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
    def _get_appreciation(self, moyenne: float) -> str:
        """Retourne l'appréciation correspondant à la moyenne"""
        if moyenne >= 16:
            return "Très Bien"
        elif moyenne >= 14:
            return "Bien"
        elif moyenne >= 12:
            return "Assez Bien"
        elif moyenne >= 10:
            return "Passable"
        return "Insuffisant"
    
    def _get_student_ranking(self, cursor, inscription_id: int, trimestre_id: int, moyenne_generale: float) -> tuple:
        """Calcule le rang de l'élève dans sa classe"""
        try:
            # Requête pour le rang
            rang_query = """
            SELECT COUNT(*) + 1 as rang
            FROM (
                SELECT 
                    ie2.id,
                    AVG(CAST(erc2.moyeperiexam as DECIMAL(5,2))) as moyenne_gen
                FROM inscriptioneleve ie2
                JOIN eduresultatcopie erc2 ON ie2.Eleve = erc2.idenelev
                WHERE ie2.Classe = (SELECT Classe FROM inscriptioneleve WHERE id = %s)
                    AND erc2.codeperiexam = %s
                    AND erc2.moyeperiexam IS NOT NULL
                    AND erc2.moyeperiexam != 0
                GROUP BY ie2.id
                HAVING moyenne_gen > %s
            ) as classement
            """
            cursor.execute(rang_query, (inscription_id, trimestre_id, moyenne_generale))
            rang_result = cursor.fetchone()
            rang = rang_result['rang'] if rang_result else 1
            
            # Requête pour l'effectif
            effectif_query = """
            SELECT COUNT(DISTINCT ie.id) as effectif
            FROM inscriptioneleve ie
            JOIN eduresultatcopie erc ON ie.Eleve = erc.idenelev
            WHERE ie.Classe = (SELECT Classe FROM inscriptioneleve WHERE id = %s)
                AND erc.codeperiexam = %s
            """
            cursor.execute(effectif_query, (inscription_id, trimestre_id))
            effectif_result = cursor.fetchone()
            effectif = effectif_result['effectif'] if effectif_result else 0
            
            return rang, effectif
        except Exception as e:
            logger.error(f"Erreur calcul rang: {e}")
            return 1, 0
    
    def _get_period_name(self, trimestre_id: int, annee_scolaire: str) -> str:
        """Retourne le nom formaté de la période"""
        trimestre_names = {
            31: "1er Trimestre",
            32: "2ème Trimestre", 
            33: "3ème Trimestre"
        }
        return f"{trimestre_names.get(trimestre_id, 'Trimestre')} {annee_scolaire}"

    def generate(self, student_data: Dict[str, Any], matieres: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Génère un bulletin PDF pour un trimestre donné"""
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Configuration des polices
            self._setup_fonts(pdf)
            
            # En-tête
            self._add_header(pdf, student_data)
            
            # Informations élève
            self._add_student_info(pdf, student_data)
            
            # Tableau des matières (uniquement si des notes existent)
            if matieres:
                self._add_grades_table(pdf, matieres)
            else:
                self._add_no_grades_message(pdf)
            
            # Résultats généraux
            self._add_summary(pdf, student_data)
            
            # Sauvegarde
            return self._save_pdf(pdf, student_data)
            
        except Exception as e:
            logger.error(f"Erreur génération bulletin: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _add_no_grades_message(self, pdf: FPDF):
        """Ajoute un message quand il n'y a pas de notes"""
        pdf.set_font("Amiri", "B", 14)
        pdf.set_y(100)
        pdf.cell(0, 10, "Aucune note disponible pour cette période", ln=True, align="C")
        pdf.ln(20)

    def _setup_fonts(self, pdf: FPDF):
        """Configure les polices Amiri"""
        pdf.add_font("Amiri", "", str(self.font_dir / "Amiri-Regular.ttf"), uni=True)
        pdf.add_font("Amiri", "B", str(self.font_dir / "Amiri-Bold.ttf"), uni=True)

    def _add_header(self, pdf: FPDF, student_info: Dict[str, Any]):
        """Ajoute l'en-tête institutionnel"""
        # Logo
        logo_path = Path(__file__).parent.parent.parent / "assets" / "logo_ise.jpeg"
        if logo_path.exists():
            pdf.image(str(logo_path), x=10, y=8, w=30)
        
        # Texte arabe
        pdf.set_font("Amiri", "", 12)
        pdf.set_xy(100, 10)
        institution_ar = self._render_arabic("المدرسة الدولية للنخبة بنابل")
        pdf.cell(0, 8, institution_ar, align="R")
        
        # Texte français
        pdf.set_font("Amiri", "", 10)
        pdf.set_xy(100, 20)
        pdf.cell(0, 6, "École Internationale de l'Élite - Nabeul", align="R")
        
        # Titre principal
        pdf.set_font("Amiri", "B", 18)
        pdf.set_y(45)
        pdf.cell(0, 12, "BULLETIN SCOLAIRE", ln=True, align="C")

    def _add_student_info(self, pdf: FPDF, student_info: Dict[str, Any]):
        """Ajoute les informations de l'élève"""
        pdf.set_font("Amiri", "", 12)
        pdf.set_y(65)
        
        infos = [
            ("Nom et Prénom", student_info["nom"]),
            ("Matricule", student_info["matricule"]),
            ("Classe", student_info["classe"]),
            ("Période", student_info["periode"])
        ]
        
        if "date_naissance" in student_info:
            infos.insert(2, ("Date de naissance", student_info["date_naissance"]))
        
        for label, value in infos:
            pdf.cell(45, 8, f"{label} :", 0, 0)
            pdf.set_font("Amiri", "B", 12)
            pdf.cell(0, 8, str(value), ln=True)
            pdf.set_font("Amiri", "", 12)
        
        pdf.ln(8)

    def _add_grades_table(self, pdf: FPDF, matieres: List[Dict[str, Any]]):
        """Ajoute le tableau des matières et notes"""
        pdf.set_font("Amiri", "B", 11)
        
        # En-tête du tableau
        headers = ["Matière", "Coeff", "Moyenne", "Appréciation"]
        col_widths = [65, 20, 25, 75]
        
        # Ligne d'en-tête avec fond gris
        pdf.set_fill_color(220, 220, 220)
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 10, header, 1, 0, "C", True)
        pdf.ln()
        
        # Données
        pdf.set_font("Amiri", "", 11)
        pdf.set_fill_color(255, 255, 255)
        
        for i, matiere in enumerate(matieres):
            # Alternance de couleurs pour les lignes
            pdf.set_fill_color(245, 245, 245) if i % 2 == 0 else pdf.set_fill_color(255, 255, 255)
            
            pdf.cell(col_widths[0], 10, matiere["nom"], 1, 0, "L", True)
            pdf.cell(col_widths[1], 10, str(matiere["coefficient"]), 1, 0, "C", True)
            pdf.cell(col_widths[2], 10, str(matiere["moyenne"]), 1, 0, "C", True)
            pdf.cell(col_widths[3], 10, matiere.get("appreciation", ""), 1, 0, "L", True)
            pdf.ln()
        
        pdf.ln(10)

    def _add_summary(self, pdf: FPDF, student_info: Dict[str, Any]):
        """Ajoute le résumé des résultats"""
        pdf.set_font("Amiri", "B", 14)
        pdf.cell(0, 10, "BILAN GÉNÉRAL", ln=True)
        pdf.ln(5)
        
        stats = [
            ("Moyenne Générale", f"{student_info.get('moyenne_generale', 'N/A')}/20"),
            ("Rang", student_info.get('rang', 'N/A')),
            ("Mention", student_info.get('mention', 'N/A'))
        ]
        
        pdf.set_font("Amiri", "", 12)
        for label, value in stats:
            pdf.cell(50, 8, f"{label} :", 0, 0)
            pdf.set_font("Amiri", "B", 12)
            pdf.cell(0, 8, str(value), ln=True)
            pdf.set_font("Amiri", "", 12)
        
        pdf.ln(15)
        
        # Signature
        pdf.cell(0, 8, f"Fait à Nabeul, le {datetime.now().strftime('%d/%m/%Y')}", ln=True)
        pdf.ln(10)
        pdf.cell(0, 8, "La Directrice", ln=True, align="R")
        pdf.set_font("Amiri", "B", 12)
        pdf.cell(0, 8, "Mme Balkis ZRELLI", ln=True, align="R")

    def _save_pdf(self, pdf: FPDF, student_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sauvegarde le PDF généré"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"bulletin_{student_data['matricule']}_T{student_data.get('trimestre_id', 'X')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = self.output_dir / filename
        
        pdf.output(str(output_path))
        
        return {
            "status": "success",
            "path": str(output_path),
            "filename": filename,
            "student_name": student_data["nom"],
            "period": student_data["periode"],
            "average": student_data.get("moyenne_generale", 0)
        }

def export_bulletin_pdf(student_id: int, trimestre_id: Optional[int] = None, 
                       annee_scolaire: Optional[str] = None) -> Dict[str, Any]:
    """
    Interface principale pour générer un ou plusieurs bulletins
    
    Args:
        student_id: ID de l'élève (matricule/IdPersonne)
        trimestre_id: ID du trimestre (31=T1, 32=T2, 33=T3). Si None, tous les trimestres.
        annee_scolaire: Année scolaire au format "2024/2025". Si None, déterminée automatiquement.
    
    Returns:
        Dict avec status et bulletins générés ou message d'erreur
    """
    try:
        generator = BulletinPDFGenerator()
        
        # Récupération des données
        student_data = generator.get_student_data_from_db(student_id, trimestre_id, annee_scolaire)
        
        if not student_data:
            return {
                "status": "error",
                "message": f"Aucune donnée disponible pour l'élève {student_id}"
            }
        
        # Si un seul trimestre demandé ou trouvé
        if isinstance(student_data, dict):
            result = generator.generate(student_data["student_data"], student_data["matieres"])
            if result["status"] == "success":
                logger.info(f"Bulletin généré pour {student_data['student_data']['nom']}")
            return result
        
        # Si plusieurs trimestres
        results = []
        for trim_data in student_data:
            result = generator.generate(trim_data["student_data"], trim_data["matieres"])
            results.append(result)
        
        # Analyse des résultats
        success_results = [r for r in results if r.get("status") == "success"]
        
        if not success_results:
            return {
                "status": "error",
                "message": "Aucun bulletin généré avec succès",
                "details": results
            }
        
        return {
            "status": "multi_success",
            "count": len(success_results),
            "bulletins": success_results
        }
        
    except Exception as e:
        logger.error(f"Erreur critique génération bulletin: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Erreur système: {str(e)}"
        }