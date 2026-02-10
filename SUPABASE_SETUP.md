# Supabase Setup Guide

This guide explains how to configure the MVP Verbatim Analysis system to use Supabase as the database backend instead of local PostgreSQL.

## 🔵 What is Supabase?

Supabase is an open-source Firebase alternative that provides:
- **PostgreSQL database** (fully compatible with our SQLAlchemy models)
- **Connection pooling** (PgBouncer)
- **REST API** (optional, not used in this MVP)
- **Authentication** (optional, not used in this MVP)
- **Real-time subscriptions** (optional)
- **Storage** (optional)

For this MVP, we only use Supabase as a **managed PostgreSQL database**.

## 📋 Prerequisites

1. A Supabase account: https://supabase.com
2. A Supabase project (free tier available)

## 🚀 Step-by-Step Setup

### 1. Create a Supabase Project

1. Go to https://app.supabase.com
2. Click "New Project"
3. Fill in:
   - **Name**: `verbatim-analysis-mvp` (or any name)
   - **Database Password**: Choose a strong password (save it!)
   - **Region**: Choose closest to your location
   - **Pricing Plan**: Free tier is sufficient for MVP
4. Click "Create new project"
5. Wait 2-3 minutes for provisioning

### 2. Get Database Connection String

1. In your Supabase project dashboard, go to:
   - **Settings** → **Database**
2. Scroll to **Connection string**
3. Select **Connection pooling** tab (recommended)
4. Copy the connection string in "URI" format:
   ```
   postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:5432/postgres
   ```
5. Replace `[YOUR-PASSWORD]` with your actual database password

### 3. Get API Credentials

1. Go to **Settings** → **API**
2. Copy:
   - **Project URL**: `https://[PROJECT-REF].supabase.co`
   - **anon public key** or **service_role key**:
     - Use `anon` for basic access
     - Use `service_role` for admin operations (keep secret!)

### 4. Configure Environment Variables

Edit your `.env` file:

```bash
# Activate Supabase
USE_SUPABASE=true

# Supabase Configuration
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_DB_URL=postgresql://postgres.xxxxx:your-password@aws-0-us-west-1.pooler.supabase.com:5432/postgres

# Local PostgreSQL is ignored when USE_SUPABASE=true
# DATABASE_URL=postgresql://verbatim_user:verbatim_password@localhost:5432/verbatim_analysis
```

### 5. Initialize Database

Run the initialization script:

```bash
# Initialize tables
python scripts/init_db.py init

# Load GIDA reference data
python scripts/load_gida.py load
```

The script will automatically detect Supabase configuration and create tables in your Supabase database.

### 6. Verify Connection

Test the connection:

```bash
python -c "from src.db.connection import test_connection; test_connection()"
```

Expected output:
```
🔵 Using Supabase as database backend
✅ Database connection successful
```

## 🔧 Troubleshooting

### Connection Timeout

**Problem**: `Connection timeout` error

**Solutions**:
1. Check your internet connection
2. Verify the connection string is correct
3. Ensure you're using the **Connection pooling** URL (not Direct connection)
4. Check Supabase project is not paused (free tier pauses after 1 week inactivity)

### Authentication Failed

**Problem**: `FATAL: password authentication failed`

**Solutions**:
1. Double-check your database password
2. Make sure you replaced `[YOUR-PASSWORD]` in the connection string
3. Try resetting the database password in Supabase dashboard

### SSL Error

**Problem**: `SSL connection error`

**Solution**: Supabase requires SSL. The connection is configured automatically. If you get SSL errors, add to connection string:
```
?sslmode=require
```

### Tables Not Created

**Problem**: Tables don't appear in Supabase dashboard

**Solutions**:
1. Check Table Editor in Supabase dashboard
2. Go to SQL Editor and run:
   ```sql
   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
   ```
3. Verify `init_db.py` script completed successfully

## 📊 Monitoring

### View Your Data in Supabase

1. Go to Supabase dashboard
2. Navigate to **Table Editor**
3. You'll see all tables:
   - `projects`
   - `project_verbatims`
   - `analysis_runs`
   - `analysis_chunks`
   - `chunk_topics`
   - `run_topics`
   - `project_ontology`
   - `run_entities`
   - `dim_ontology_entities`
   - `dim_ontology_attributes`
   - `processing_logs`

### Query Database

Use the **SQL Editor** tab to run queries:

```sql
-- Count verbatims
SELECT COUNT(*) FROM project_verbatims;

-- List projects
SELECT id, name, source_type, created_at FROM projects;

-- Check analysis runs
SELECT id, mode, status, created_at FROM analysis_runs;
```

### Monitor Performance

1. Go to **Reports** tab
2. View:
   - Database size
   - Connection count
   - Query performance
   - Resource usage

## 🔐 Security Best Practices

### API Keys

- ✅ **anon key**: Safe to use in client-side code (has Row Level Security)
- ⚠️ **service_role key**: Keep secret! Has admin access. Use for backend only.

For this MVP, since everything runs server-side (Streamlit), you can use either key.

### Row Level Security (RLS)

Supabase uses PostgreSQL Row Level Security. For this MVP:
- **Option 1**: Disable RLS (development/testing)
- **Option 2**: Enable RLS and create policies (production)

To disable RLS for a table (via SQL Editor):
```sql
ALTER TABLE projects DISABLE ROW LEVEL SECURITY;
ALTER TABLE project_verbatims DISABLE ROW LEVEL SECURITY;
-- Repeat for all tables
```

### Database Backups

Free tier includes:
- Point-in-time recovery (7 days)
- Daily backups

Access via: **Settings** → **Database** → **Backups**

## 💰 Cost Considerations

### Free Tier Limits
- **Database**: 500 MB
- **Bandwidth**: 2 GB
- **API Requests**: Unlimited
- **Projects**: 2 active projects
- **Pausing**: After 1 week inactivity (can be reactivated)

### Estimated Usage for MVP
- **50,000 verbatims**: ~100-200 MB
- **Typical analysis run**: ~10-50 MB
- **With 10 projects**: ~300-500 MB (within free tier)

### Upgrade if Needed
- **Pro tier** ($25/month): 8 GB database, 50 GB bandwidth
- **Pay as you go**: Available for larger needs

## 🔄 Switching Back to Local PostgreSQL

To switch back to local PostgreSQL:

1. Edit `.env`:
   ```bash
   USE_SUPABASE=false
   ```
2. Restart application
3. System will use local `DATABASE_URL` again

## 🆘 Support

- **Supabase Docs**: https://supabase.com/docs
- **Community**: https://github.com/supabase/supabase/discussions
- **Status**: https://status.supabase.com

## ✅ Checklist

- [ ] Supabase project created
- [ ] Database password saved securely
- [ ] Connection string copied
- [ ] API keys copied
- [ ] `.env` file updated with Supabase credentials
- [ ] `USE_SUPABASE=true` set
- [ ] Database initialized (`init_db.py`)
- [ ] GIDA data loaded (`load_gida.py`)
- [ ] Connection tested successfully
- [ ] Streamlit app launched and working

---

**Note**: Supabase uses standard PostgreSQL, so all existing SQLAlchemy models, queries, and migrations work without modification! 🎉
