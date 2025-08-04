from fpdf import FPDF
from pathlib import Path
import os
import arabic_reshaper
from bidi.algorithm import get_display

def export_attestation_pdf(donnees):
    pdf = FPDF()
    pdf.add_page()

    base_path = Path(__file__).parent

    # Police dans: agent/pdf_utils/fonts/Amiri-1.002/
    font_dir = base_path / "fonts" / "Amiri-1.002"
    font_path_regular = font_dir / "Amiri-Regular.ttf"
    font_path_bold = font_dir / "Amiri-Bold.ttf"

    # Conversion en chemin absolu
    font_path_regular = str(font_path_regular.resolve())
    font_path_bold = str(font_path_bold.resolve())

    # Ajout des polices au PDF
    pdf.add_font("Amiri", "", font_path_regular, uni=True)
    pdf.add_font("Amiri", "B", font_path_bold, uni=True)

    pdf.set_font("Amiri", size=14)

    def render_ar(text):
        return get_display(arabic_reshaper.reshape(text))

    logo_path = "C:/Users/rania/Downloads/logo_ise.jpeg"
    if os.path.exists(logo_path):
        pdf.image(logo_path, x=10, y=10, w=30)

    pdf.set_xy(110, 10)
    pdf.multi_cell(
        0, 8,
        render_ar("الجمهورية التونسية\nوزارة التربية\nالمندوبية الجهوية للتربية بنابل\nالمدرسة الدولية للنخبة"),
        align='R'
    )

    pdf.ln(30)

    pdf.set_font("Amiri", 'B', 16)
    pdf.cell(0, 10, "ATTESTATION DE PRÉSENCE", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Amiri", '', 14)
    texte_intro = (
        "Je soussignée, Mme Balkis Zrelli, Directrice du Collège et Lycée International School Of Elite, atteste que:\n"
    )
    pdf.multi_cell(0, 10, texte_intro)

    nom = donnees.get('nom_complet') or donnees.get('nom') or 'Nom non précisé'
    pdf.set_font("Amiri", 'B', 16)
    pdf.cell(0, 10, nom.upper(), ln=True, align='C')

    classe = donnees.get('classe', 'Classe non précisée')
    pdf.set_font("Amiri", '', 14)
    texte_avant_classe = "Est inscrit(e) et poursuit régulièrement ses études en "
    texte_apres_classe = " de l'année scolaire 2024/2025\nEn foi de quoi, la présente attestation lui est établie pour servir et valoir ce que de droit.\n"

    pdf.write(8, texte_avant_classe)
    pdf.set_font("Amiri", 'B', 14)
    pdf.write(8, classe)
    pdf.set_font("Amiri", '', 14)
    pdf.write(8, texte_apres_classe)

    pdf.ln(20)
    pdf.cell(0, 10, "Signature & Cachet :", ln=True, align='R')
    pdf.cell(0, 10, "_______________________", ln=True, align='R')

    # Sauvegarde dans static/attestations/
    output_dir = Path("static/attestations")
    output_dir.mkdir(parents=True, exist_ok=True)

    matricule = donnees.get('matricule', '0000')
    filename = f"attestation_presence_{matricule}.pdf"
    chemin = output_dir / filename

    pdf.output(str(chemin))
    return str(chemin)
