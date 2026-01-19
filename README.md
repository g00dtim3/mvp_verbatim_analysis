# MVP Analyse Verbatims

Outil d'analyse quali/quanti de verbatims issus de Brandwatch et Semantiweb.

## 🏗️ Stack Technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Python 3.13 |
| Notebooks | Jupyter |
| Base de données | PostgreSQL 15+ / Supabase |
| Frontend | Streamlit |
| Hosting | Streamlit Cloud / Posit Connect |
| LLM | OpenAI GPT-4 |
| Orchestration | LangGraph |

## 📁 Structure du Projet

```
mvp_verbatim_analysis/
├── notebooks/                 # Jupyter notebooks
│   ├── 01_spike_langgraph.ipynb
│   ├── 02_data_exploration.ipynb
│   └── 03_prompt_tuning.ipynb
├── src/
│   ├── api/                   # Logique métier
│   │   ├── import_csv.py
│   │   ├── cleaning.py
│   │   ├── deduplication.py
│   │   ├── analysis_llm.py
│   │   ├── merge_topics.py
│   │   ├── quantification.py
│   │   └── export.py
│   ├── db/                    # Base de données
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── queries.py
│   ├── llm/                   # Intégration LLM
│   │   ├── client.py
│   │   ├── prompts.py
│   │   └── langgraph_pipeline.py
│   └── utils/                 # Utilitaires
│       ├── config.py
│       └── helpers.py
├── app/                       # Streamlit
│   ├── app.py                 # Point d'entrée
│   └── pages/
│       ├── 1_import.py
│       ├── 2_cleaning.py
│       ├── 3_analysis.py
│       ├── 4_quantification.py
│       └── 5_exploration.py
├── data/
│   ├── uploads/               # Fichiers uploadés
│   └── gida/                  # Référentiel GIDA
├── scripts/
│   ├── init_db.py             # Initialisation DB
│   └── migrate.py             # Migrations
├── tests/
├── .env.example
├── requirements.txt
├── docker-compose.yml
└── README.md
```

## 🚀 Installation

### Prérequis

- Python 3.13
- PostgreSQL 15+ (ou compte Supabase gratuit)
- Compte OpenAI avec accès API

### 1. Cloner et configurer

```bash
git clone <repo_url>
cd mvp_verbatim_analysis

# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env avec vos valeurs
nano .env
```

### 3. Base de données

Trois options disponibles :

```bash
# Option A : Docker PostgreSQL (recommandé pour dev local)
docker-compose up -d db
python scripts/init_db.py init
python scripts/load_gida.py load

# Option B : Supabase (recommandé pour production)
# 1. Créer un projet sur https://supabase.com
# 2. Configurer USE_SUPABASE=true dans .env
# 3. Ajouter vos credentials Supabase
# Voir SUPABASE_SETUP.md pour le guide complet
python scripts/init_db.py init
python scripts/load_gida.py load

# Option C : PostgreSQL local
# Créer la base manuellement puis :
python scripts/init_db.py init
python scripts/load_gida.py load
```

### 4. Lancer l'application

```bash
# Streamlit
streamlit run app/app.py

# Ou Jupyter pour exploration
jupyter notebook notebooks/
```

## 🔧 Configuration

Variables d'environnement (`.env`) :

```env
# Base de données
DATABASE_URL=postgresql://user:password@localhost:5432/verbatim_analysis

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview

# Application
DEBUG=true
MAX_VERBATIMS=30000
CHUNK_SIZE=200
```

## 📊 Workflow

1. **Import** → Upload CSV Brandwatch/Semantiweb
2. **Nettoyage** → Options configurables + déduplication
3. **Analyse LLM** → Mode Rapide (750) ou Complet (chunking)
4. **Fusion** → 2 passes (algorithmique + LLM)
5. **Quantification** → Comptage Python déterministe
6. **Export** → Excel, CSV, Markdown

## 🧪 Tests

```bash
pytest tests/ -v
```

## 📝 Notebooks

| Notebook | Description |
|----------|-------------|
| `01_spike_langgraph.ipynb` | POC orchestration LangGraph |
| `02_data_exploration.ipynb` | Exploration datasets test |
| `03_prompt_tuning.ipynb` | Optimisation prompts LLM |

## 🚢 Déploiement

### Streamlit Cloud (Recommandé)

1. Connecter le repo GitHub à Streamlit Cloud
2. Configurer les secrets dans l'interface (Settings > Secrets):
   ```toml
   OPENAI_API_KEY = "sk-..."
   SUPABASE_URL = "https://xxx.supabase.co"
   SUPABASE_KEY = "eyJ..."
   SUPABASE_DB_URL = "postgresql+psycopg://..."
   USE_SUPABASE = "true"
   ```
3. Déployer automatiquement depuis la branche principale

### Posit Connect

```bash
# Publier sur Posit Connect
rsconnect deploy streamlit app/ --name verbatim-analysis
```

### Notes Python 3.13

Le projet est entièrement compatible Python 3.13 avec:
- ✅ SQLAlchemy 2.0.36+ (support Python 3.13)
- ✅ psycopg3 (psycopg[binary] 3.3.2)
- ✅ pandas 2.2.3+ (wheels precompilés)
- ✅ pydantic 2.10.3+ (wheels precompilés)
- ✅ tiktoken 0.8.0+ (wheels precompilés)

## 📄 License

Propriétaire - Usage interne uniquement
