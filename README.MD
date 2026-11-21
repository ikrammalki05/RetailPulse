# RetailPulse — Data Engineering & Business Analytics

**RetailPulse** est une plateforme d'analyse de données retail développée à partir du jeu de données [Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii).

Le projet couvre le cycle de traitement des données, de l'ingestion des transactions à leur transformation en données analytiques stockées dans PostgreSQL. Il intègre également un dashboard interactif permettant d'explorer les performances commerciales et le comportement des clients.

## Fonctionnalités

### Data Engineering
- Architecture Medallion : Bronze, Silver et Gold.
- Ingestion et traitement de plus d'un million de transactions.
- Nettoyage, transformation et validation des données.
- Stockage des données analytiques au format Parquet.
- Chargement des tables Gold dans PostgreSQL.
- Tests automatisés de qualité des données.

### Business Analytics

Le dashboard, développé avec Streamlit et Plotly, propose six espaces d'analyse :

| Page | Fonctionnalités |
|---|---|
| Executive Overview | Vue globale des indicateurs commerciaux et des tendances |
| Sales Analytics | Analyse du chiffre d'affaires et des ventes par période et par pays |
| Product Analytics | Classement et analyse des performances des produits |
| Customer Analytics | Analyse du comportement client et segmentation RFM |
| Returns & Cancellations | Exploration des retours et des annulations |
| Data Quality & Monitoring | Indicateurs de qualité et historique ETL depuis `gold.etl_load_log` |

Les filtres de dates et de pays sont partagés entre les différentes pages afin de conserver le même périmètre d'analyse.

Les tableaux peuvent être exportés au format CSV à la demande. Les résultats des analyses ne sont pas enregistrés dans PostgreSQL.

## Architecture

```text
Online Retail II
       |
       v
  Bronze Layer
  Raw Data
       |
       v
  Silver Layer
  Cleaning & Transformation
       |
       v
   Gold Layer
  Analytical Datasets
       |
       v
   PostgreSQL
       |
       v
 Streamlit Dashboard
       |
       v
  Plotly Visualizations
```

## Technologies utilisées

- **Langage :** Python
- **Data Processing :** Pandas, NumPy
- **Database :** PostgreSQL
- **Data Storage :** Parquet
- **Database Connectivity :** SQLAlchemy
- **Dashboard :** Streamlit
- **Visualizations :** Plotly
- **Testing :** Pytest
- **Version Control :** Git

## Installation et lancement

### Prérequis

- Python 3.11
- PostgreSQL 17 ou une version compatible
- Accès aux tables Gold de la base de données RetailPulse

### 1. Récupérer le projet

```powershell
git clone <URL_DU_DEPOT>
cd RetailPulse
```

### 2. Configurer l'environnement

Créer un environnement virtuel si nécessaire :

```powershell
python -m venv .venv
```

Installer les dépendances :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Configurer la connexion PostgreSQL

Créer le fichier `.env` à partir du modèle fourni :

```powershell
Copy-Item .env.example .env
```

Renseigner les paramètres de connexion :

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=retailpulse
DB_USER=retailpulse_reader
DB_PASSWORD=votre_mot_de_passe
```

Si le fichier `.env` existe déjà, modifier uniquement les variables nécessaires.

### 4. Lancer le dashboard

Depuis le répertoire du projet :

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Le dashboard sera accessible à l'adresse locale affichée dans le terminal, généralement :

`http://localhost:8501`

## Préparer une image Docker pour un hébergement 24/7

Le projet fournit un `Dockerfile` autonome pour Streamlit. Il ne copie pas les
données brutes ni les secrets dans l'image. La plateforme doit fournir les
variables `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` et `DB_PASSWORD` au runtime.
La base PostgreSQL doit accepter la connexion depuis l'hébergeur et le rôle
utilisé doit rester en lecture seule.

Sur un hôte Docker, construisez l'image puis démarrez-la avec un fichier de
variables protégé, par exemple :

```sh
docker build -t retailpulse-dashboard .
docker run -d --name retailpulse-dashboard --restart unless-stopped \
  --env-file /chemin/protege/retailpulse.env -p 8501:8501 retailpulse-dashboard
```

Configurez HTTPS et, si le tableau de bord est privé, l'authentification SSO
sur l'hébergeur ou un reverse proxy. N'ouvrez pas PostgreSQL au public. Le
lien `192.168.x.x` est une adresse de réseau local : l'hébergeur fournira un
nouveau domaine ou une URL publique. La base actuellement présente sur votre
PC devra être migrée vers PostgreSQL hébergé ou rendue accessible de manière
sécurisée depuis le serveur.

## Sécurité et accès à la base de données

Le dashboard utilise un compte PostgreSQL dédié en lecture seule : `retailpulse_reader`.

- Les identifiants sont configurés côté serveur, jamais dans le navigateur.
- Les requêtes SQL sont paramétrées et exécutées dans des transactions en lecture seule.
- Les résultats des requêtes sont mis en cache pendant cinq minutes.
- Les fichiers `.env` et `.streamlit/secrets.toml` sont exclus du dépôt Git.
- En production, les identifiants doivent être configurés dans les secrets de la plateforme d'hébergement.

Le compte applicatif dispose uniquement des permissions nécessaires à la consultation des tables Gold. Il ne peut pas modifier les données.

Un administrateur PostgreSQL peut créer ce compte à l'aide du script :

`scripts/create_dashboard_reader.sql`

Le mot de passe doit être remplacé par un secret unique avant l'exécution du script.

**Important :** la sécurité de la connexion PostgreSQL est distincte de l'authentification des utilisateurs du dashboard. Si l'application n'est pas destinée à être publique, son accès doit également être protégé par le fournisseur d'hébergement ou un système SSO.

## Définitions et périmètre des indicateurs

Pour garantir une interprétation correcte des résultats :

- **Chiffre d'affaires :** calculé à partir des lignes classées `sale` dans la couche Gold.
- **Retours et annulations :** analysés séparément des ventes valides.
- **Recency (R) :** nombre de jours écoulés depuis le dernier achat du client.
- **Frequency (F) :** nombre de factures associées au client.
- **Monetary (M) :** chiffre d'affaires généré par le client identifié.

La segmentation RFM est recalculée en fonction de la période sélectionnée dans le dashboard. Les transactions sans identifiant client ne sont pas intégrées à la segmentation RFM.

## Objectif du projet

RetailPulse met en pratique des concepts de Data Engineering et de Business Intelligence à travers un cas concret de données retail : construire un pipeline de traitement structuré, garantir la qualité des données et rendre les informations accessibles à travers des analyses interactives.

## Déploiement Oracle Cloud

Une procédure de déploiement sur une VM OCI avec PostgreSQL 17 persistant,
restauration des tables Gold et rôle dashboard en lecture seule est disponible
dans [deploy/oracle/README.md](deploy/oracle/README.md). Le paquet source peut
être préparé sans données brutes ni `.env` avec
`scripts/package_oracle_deploy.py`.
