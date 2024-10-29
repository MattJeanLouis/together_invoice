import streamlit as st
import pandas as pd
import tempfile
import os
import base64
import json
from io import BytesIO
from invoice2data import extract_data
from invoice2data.extract.loader import read_templates

# Importer les bibliothèques nécessaires pour l'OCR
import pytesseract
from pdf2image import convert_from_path
import pdfplumber

# Configuration de la langue pour Tesseract
os.environ['TESSDATA_PREFIX'] = '/usr/share/tesseract-ocr/4.00/tessdata/'
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# Ajout d'une fonction de logging
def log_info(message, container=None):
    if container:
        container.info(f"ℹ️ {message}")
    print(f"INFO: {message}")

def log_error(message, error=None, container=None):
    error_details = f"\nDétails: {str(error)}" if error else ""
    if container:
        container.error(f"❌ {message}{error_details}")
    print(f"ERROR: {message}{error_details}")

def log_success(message, container=None):
    if container:
        container.success(f"✅ {message}")
    print(f"SUCCESS: {message}")

# Fonction pour extraire le texte avec pdfplumber
def extract_text_from_pdf(pdf_path, log_container=None):
    try:
        log_info(f"Début de l'extraction du texte du fichier: {pdf_path}", log_container)
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            total_pages = len(pdf.pages)
            log_info(f"Nombre total de pages: {total_pages}", log_container)
            
            for i, page in enumerate(pdf.pages, 1):
                log_info(f"Traitement de la page {i}/{total_pages}", log_container)
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    log_info(f"Page {i}: Aucun texte extrait", log_container)
                    
        if text.strip():
            log_success("Extraction du texte réussie", log_container)
            return text
        else:
            log_error("Le texte extrait est vide", container=log_container)
            return None
    except Exception as e:
        log_error("Erreur lors de l'extraction du texte", e, log_container)
        return None

# Titre de l'application
st.title('📄 Extraction Automatique de Données de Factures PDF')

# Charger les modèles de factures depuis le dossier templates/
templates = read_templates('templates/')

# Initialiser une liste pour stocker les données de toutes les factures accumulées
if 'all_invoices' not in st.session_state:
    st.session_state['all_invoices'] = []

# Initialiser une liste pour stocker les informations de debug
if 'debug_info' not in st.session_state:
    st.session_state['debug_info'] = []

# Téléchargement de plusieurs fichiers PDF
uploaded_files = st.file_uploader(
    'Choisissez un ou plusieurs fichiers PDF',
    type='pdf',
    accept_multiple_files=True
)

if uploaded_files:
    for idx, uploaded_file in enumerate(uploaded_files):
        # Créer un expander pour les logs de ce fichier
        with st.expander(f"🔍 Logs - {uploaded_file.name}", expanded=False):
            log_container = st.container()
            
            log_info(f"Début du traitement du fichier: {uploaded_file.name}", log_container)
            
            # Affichage des informations sur les modèles disponibles
            log_info("Modèles disponibles:", log_container)
            for template in templates:
                try:
                    log_info(f"- Modèle pour: {template.template['issuer']}", log_container)
                    log_info(f"  Keywords: {template.template['keywords']}", log_container)
                except Exception as e:
                    log_info(f"- Modèle non identifié: {str(e)}", log_container)

            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name
                log_info(f"Fichier temporaire créé: {tmp_file_path}", log_container)

            try:
                text = extract_text_from_pdf(tmp_file_path, log_container)
                if text:
                    log_info(f"Taille du texte extrait: {len(text)} caractères", log_container)
                    st.subheader(f'Texte brut extrait - {uploaded_file.name}')
                    st.text_area('Texte brut', text, height=200, key=f'raw_text_{idx}')
                    
                    log_info("Début de l'extraction des données avec les modèles...", log_container)
                    
                    data = extract_data(
                        tmp_file_path,
                        templates=templates
                    )
                    
                    if data:
                        log_success(f"Données extraites avec succès: {list(data.keys())}", log_container)
                    else:
                        log_error("L'extraction n'a retourné aucune donnée", container=log_container)
                        log_info("Contenu du texte qui n'a pas été reconnu:", log_container)
                        log_info("=" * 50, log_container)
                        log_info(text[:500] + "..." if len(text) > 500 else text, log_container)
                        log_info("=" * 50, log_container)

                else:
                    log_error(f"Échec de l'extraction du texte pour {uploaded_file.name}", container=log_container)
                    continue

            except Exception as e:
                import traceback
                log_error(f"Erreur lors du traitement du fichier {uploaded_file.name}", e, log_container)
                log_error(f"Stack trace complète:", traceback.format_exc(), log_container)
                os.unlink(tmp_file_path)
                continue

            # Nettoyage des fichiers temporaires
            os.unlink(tmp_file_path)

            if data:
                # Afficher le texte extrait pour vérification
                st.subheader(f'Texte extrait de la facture - {uploaded_file.name}')
                st.text_area('Texte extrait', data.get('text', ''), height=200, key=f'extracted_text_{idx}')

                # Afficher les données extraites
                st.write(f'**Données extraites de {uploaded_file.name} :**')
                st.json(data)

                # Ajouter les données à la liste accumulée
                invoice_data = {
                    'Nom du fichier': uploaded_file.name,
                    'Numéro de facture': data.get('invoice_number', 'N/A'),
                    'Date de facturation': data.get('date', 'N/A'),
                    'Montant total': data.get('amount', 'N/A'),
                    'Nom du client': data.get('client', 'N/A'),
                    'Nom du vendeur': data.get('issuer', 'N/A'),
                }
                st.session_state['all_invoices'].append(invoice_data)

                # Stocker les informations de debug
                debug_info = {
                    'filename': uploaded_file.name,
                    'extracted_text': text,
                    'parsed_data': data,
                    'excel_row': invoice_data
                }
                st.session_state['debug_info'].append(debug_info)
            else:
                st.warning(f"Aucun modèle n'a pu extraire les données pour la facture {uploaded_file.name}")

# Si des factures ont été accumulées, afficher le tableau et offrir l'option de téléchargement
if st.session_state['all_invoices']:
    df = pd.DataFrame(st.session_state['all_invoices'])
    st.subheader('Aperçu des données accumulées')
    st.dataframe(df)

    # Fonction pour générer un lien de téléchargement pour le fichier Excel
    def get_table_download_link(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        processed_data = output.getvalue()
        b64 = base64.b64encode(processed_data).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="factures_aggregées.xlsx">📥 Télécharger le fichier Excel</a>'
        return href

    # Afficher le bouton de téléchargement
    st.markdown(get_table_download_link(df), unsafe_allow_html=True)

    # Section de debug dans un expander
    with st.expander("🐛 Informations de Debug", expanded=False):
        st.write("Ces informations sont utiles pour le débogage des modèles de facture.")
        
        # Créer le texte de debug pour toutes les factures
        debug_text = ""
        for info in st.session_state['debug_info']:
            debug_text += f"\n{'='*50}\n"
            debug_text += f"Fichier: {info['filename']}\n\n"
            debug_text += f"Texte Extrait:\n{info['extracted_text']}\n\n"
            debug_text += f"Données Parsées:\n{json.dumps(info['parsed_data'], indent=2)}\n\n"
            debug_text += f"Données Excel:\n{json.dumps(info['excel_row'], indent=2)}\n"
            debug_text += f"{'='*50}\n"

        # Afficher le texte dans une zone de texte
        st.text_area("Informations complètes de debug", debug_text, height=400)

        # Bouton pour copier les informations de debug
        if st.button("📋 Copier les informations de debug"):
            st.code(debug_text)
            st.success("Les informations de debug ont été formatées. Utilisez le bouton de copie ci-dessus pour les copier.")

else:
    st.info("Ajoutez des factures pour extraire les données et les accumuler dans un fichier Excel.")
