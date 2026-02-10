# Configuration Streamlit Cloud - Guide Rapide

## 🔑 Configuration des Secrets

### 1. Accéder aux Secrets

1. Ouvrir votre app sur Streamlit Cloud
2. Cliquer sur **"Manage app"** (coin inférieur droit)
3. Aller dans l'onglet **"Settings"**
4. Cliquer sur **"Secrets"**

### 2. Obtenir les Credentials

#### OpenAI API Key

1. Aller sur https://platform.openai.com/api-keys
2. Se connecter avec votre compte OpenAI
3. Cliquer sur **"Create new secret key"**
4. Donner un nom (ex: "streamlit-verbatim-analysis")
5. Copier la clé (commence par `sk-proj-...` ou `sk-...`)
6. ⚠️ **IMPORTANT**: Sauvegarder la clé immédiatement - elle ne sera plus visible après

#### Supabase Credentials

1. Aller sur https://supabase.com/dashboard
2. Sélectionner votre projet
3. Aller dans **Settings** > **API**
4. Copier:
   - **Project URL** (ex: `https://xxxxx.supabase.co`)
   - **Project API Key** (anon/public key)
5. Aller dans **Settings** > **Database**
6. Dans la section **Connection string** > **URI**, copier l'URL de connection
7. ⚠️ Remplacer `postgresql://` par `postgresql+psycopg://` dans l'URL
8. ⚠️ Utiliser le **Connection pooler** (port 6543, mode Transaction)

### 3. Coller les Secrets dans Streamlit Cloud

Dans l'éditeur de secrets, coller le contenu suivant (remplacer les valeurs par les vôtres):

```toml
# ============================================
# OpenAI Configuration
# ============================================
OPENAI_API_KEY = "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
OPENAI_MODEL = "gpt-4-turbo-preview"
OPENAI_MAX_TOKENS = "4096"
OPENAI_TEMPERATURE = "0.1"

# ============================================
# Supabase Configuration
# ============================================
SUPABASE_URL = "https://xxxxxxxxxxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
SUPABASE_DB_URL = "postgresql+psycopg://postgres.xxxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
USE_SUPABASE = "true"

# ============================================
# Application Configuration
# ============================================
DEBUG = "false"
LOG_LEVEL = "INFO"
MAX_VERBATIMS = "50000"
CHUNK_SIZE = "200"
SAMPLE_SIZE_RAPID = "750"
```

### 4. Format de l'URL Supabase

L'URL de connexion Supabase doit avoir ce format précis:

```
postgresql+psycopg://postgres.PROJECT_REF:PASSWORD@REGION.pooler.supabase.com:6543/postgres
```

**Exemple complet:**
```
postgresql+psycopg://postgres.abcdefghijklmnop:myP@ssw0rd123@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

**Points clés:**
- ✅ Commence par `postgresql+psycopg://` (pas `postgresql://`)
- ✅ Utilise le port **6543** (connection pooler)
- ✅ Finit par `/postgres` (nom de la base)

### 5. Vérifier la Configuration

Après avoir sauvegardé les secrets:

1. L'app va redémarrer automatiquement
2. Sur la page d'accueil, vérifier:
   - ✅ **Database**: Connection OK
   - ✅ **OpenAI**: API OK
3. Si erreur:
   - Cliquer sur "Manage app" > "Logs" pour voir les détails
   - Vérifier que les secrets sont bien formatés (pas d'espaces, guillemets corrects)

## 🗄️ Initialisation de la Base de Données

### 1. Créer les Tables

1. Aller sur https://supabase.com/dashboard
2. Sélectionner votre projet
3. Cliquer sur **SQL Editor** (dans le menu latéral)
4. Créer une nouvelle query
5. Copier le contenu de `sql/create_tables.sql`
6. Cliquer sur **Run** (ou Ctrl+Enter)
7. Vérifier qu'il n'y a pas d'erreurs

### 2. Charger les Données GIDA

1. Dans le SQL Editor, créer une nouvelle query
2. Copier le contenu de `sql/insert_gida_data.sql`
3. Cliquer sur **Run**
4. Vérifier l'insertion: vous devriez voir "22 rows affected"

### 3. Vérifier les Tables

```sql
-- Lister toutes les tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Vérifier les données GIDA
SELECT entity_type, COUNT(*)
FROM dim_ontology_entities
WHERE ontology_version = '2026.01'
GROUP BY entity_type;

SELECT attribute_type, COUNT(*)
FROM dim_ontology_attributes
WHERE ontology_version = '2026.01'
GROUP BY attribute_type;
```

Vous devriez voir:
- **11 tables** créées
- **15 entities** GIDA (5 pathologies, 5 brands, 5 zones)
- **7 attributes** GIDA

## 🐛 Dépannage

### Erreur: "Invalid API key"

**Symptôme:** `Error code: 401 - Incorrect API key provided`

**Solution:**
1. Vérifier que la clé OpenAI commence bien par `sk-proj-` ou `sk-`
2. Vérifier qu'il n'y a pas d'espaces avant/après
3. Vérifier que les guillemets sont bien des `"` (pas des `'`)
4. Créer une nouvelle clé API si nécessaire

### Erreur: "ModuleNotFoundError: psycopg2"

**Symptôme:** SQLAlchemy ne trouve pas psycopg2

**Solution:**
1. Vérifier que l'URL commence par `postgresql+psycopg://`
2. **Ne pas** utiliser `postgresql://` (cherche psycopg2)
3. Redémarrer l'app après modification des secrets

### Erreur: "Connection timeout"

**Symptôme:** Timeout lors de la connexion à Supabase

**Solution:**
1. Vérifier que vous utilisez le **Connection pooler** (port 6543)
2. Ne pas utiliser le port 5432 (connexion directe, limitée)
3. Vérifier que le mot de passe ne contient pas de caractères spéciaux non encodés

### Erreur: "SSL required"

**Solution:**
Ajouter `?sslmode=require` à la fin de l'URL:
```
postgresql+psycopg://...postgres?sslmode=require
```

## 📊 Limites et Quotas

### Supabase (Free Tier)

- ✅ 500 MB de stockage
- ✅ 2 GB de transfert/mois
- ✅ 50,000 requêtes/mois
- ⚠️ Pause après 7 jours d'inactivité

Pour des projets de production, considérer le plan **Pro** ($25/mois).

### OpenAI

- Tarification à l'usage (pay-as-you-go)
- GPT-4 Turbo: ~$0.01 par 1K tokens input, ~$0.03 par 1K output
- Estimation pour analyse de 1000 verbatims: $5-15 selon mode (rapide/complet)

**Astuce:** Définir une limite de dépense mensuelle dans votre compte OpenAI.

## ✅ Checklist de Déploiement

- [ ] Créer projet Supabase
- [ ] Obtenir clé API OpenAI
- [ ] Configurer les secrets dans Streamlit Cloud
- [ ] Vérifier le format de l'URL Supabase (commence par `postgresql+psycopg://`)
- [ ] Exécuter `sql/create_tables.sql` dans Supabase SQL Editor
- [ ] Exécuter `sql/insert_gida_data.sql` dans Supabase SQL Editor
- [ ] Vérifier que l'app démarre sans erreur
- [ ] Tester l'import d'un fichier CSV
- [ ] Vérifier que les données sont bien insérées en base

## 📞 Support

En cas de problème:
1. Vérifier les logs: **Manage app** > **Logs**
2. Vérifier la documentation Supabase: https://supabase.com/docs
3. Consulter les issues GitHub du projet

---

*Dernière mise à jour: 2026-01-22*
