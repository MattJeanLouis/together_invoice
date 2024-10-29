# Extracteur de Données de Factures

Application web permettant d'extraire automatiquement les données de factures PDF et de les exporter en Excel.

## Lancement avec Docker

```bash
# Construire l'image
docker build -t facture-extractor .

# Lancer l'application
docker run -p 8501:8501 facture-extractor
```

L'application sera accessible sur `http://localhost:8501`

## Ajout de Modèles invoice2data

1. Créez un fichier YAML dans le dossier `templates/`
2. Structure du modèle:
```yaml
issuer: Nom de l'entreprise
keywords:
  - mot-clé1
  - mot-clé2
fields:
  amount: montant_regexp
  date: date_regexp
  invoice_number: numero_regexp
  client: client_regexp
```

## Fonctionnalités

- Upload multiple de factures PDF
- Extraction automatique des données via OCR
- Visualisation des données extraites
- Export Excel des résultats
- Support multilingue (FR/EN)
- Affichage des logs d'extraction
- Mode debug pour le développement de modèles
