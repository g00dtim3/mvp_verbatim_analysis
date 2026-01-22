# Gestion des Topics et Ontologies - Architecture

## 📋 Question

**Comment gérer les topics et ontologies générés par chaque analyse sur le long terme?**

Chaque analyse LLM génère de nouveaux thèmes (topics) et leurs ontologies associées (keywords, regex). Comment éviter la duplication et organiser ces données dans la base?

## 🏗️ Architecture Actuelle (MVP)

### Principe: **Isolation par Run**

Chaque `AnalysisRun` a ses propres topics et ontologies **isolés** et indépendants:

```
AnalysisRun (run_id_1)
├── RunTopic 1 ("Efficacité du produit")
│   └── ProjectOntology (keywords: ["efficace", "fonctionne"...])
├── RunTopic 2 ("Prix")
│   └── ProjectOntology (keywords: ["cher", "coût"...])
└── ...

AnalysisRun (run_id_2)  ← Nouveau run, nouveaux topics
├── RunTopic 1 ("Qualité produit")  ← Peut ressembler à "Efficacité" mais indépendant
│   └── ProjectOntology (keywords différents)
└── ...
```

### Avantages de cette approche

✅ **Traçabilité complète**: Chaque run est immuable et auditable
✅ **Pas de conflits**: Pas de collisions entre analyses
✅ **Comparaison facile**: On peut comparer l'évolution des thèmes entre runs
✅ **Rollback simple**: On peut revenir à une version antérieure
✅ **Expérimentation**: Différents briefs → différents thèmes

### Inconvénients

❌ **Duplication de données**: "Prix" peut apparaître dans 10 runs différents
❌ **Pas de consolidation**: Difficile d'avoir une vue globale des thèmes récurrents
❌ **Croissance de la base**: Chaque run ajoute N topics × leurs ontologies

## 🎯 Architecture Future: Ontologie Centralisée

### Phase 1: Consolidation manuelle (MVP+)

Ajouter une fonctionnalité permettant à un analyste de **consolider manuellement** les topics après analyse:

```sql
-- Nouvelle table pour les topics "masters"
CREATE TABLE master_topics (
    id UUID PRIMARY KEY,
    canonical_label VARCHAR(255) NOT NULL,
    consolidated_keywords JSONB,
    usage_count INTEGER DEFAULT 1,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    created_by VARCHAR(255)
);

-- Table de mapping run_topic → master_topic
CREATE TABLE topic_mappings (
    id UUID PRIMARY KEY,
    run_topic_id UUID REFERENCES run_topics(id),
    master_topic_id UUID REFERENCES master_topics(id),
    mapped_by VARCHAR(255),
    mapped_at TIMESTAMP,
    confidence_score FLOAT
);
```

**Workflow:**
1. Analyste lance une analyse → génère des `run_topics`
2. L'UI propose de mapper aux `master_topics` existants (fuzzy matching)
3. Analyste valide/corrige le mapping
4. Les ontologies se consolident automatiquement

### Phase 2: Recommandation automatique (Advanced)

Utiliser un LLM pour suggérer automatiquement les mappings:

```python
def suggest_topic_mapping(new_topic: RunTopic, threshold: float = 0.85):
    """Suggère des master_topics similaires."""
    existing_masters = db.query(MasterTopic).all()

    for master in existing_masters:
        similarity = calculate_semantic_similarity(
            new_topic.canonical_label,
            master.canonical_label,
            new_topic.keywords,
            master.consolidated_keywords
        )

        if similarity > threshold:
            yield {
                'master_topic': master,
                'confidence': similarity,
                'reason': 'Semantic similarity + keyword overlap'
            }
```

### Phase 3: Apprentissage continu (Enterprise)

Le système apprend des mappings validés pour améliorer ses suggestions:

```python
class TopicConsolidationEngine:
    """
    Moteur d'apprentissage pour la consolidation de topics.
    """

    def train_from_history(self):
        """Apprend des mappings validés précédents."""
        validated_mappings = db.query(TopicMapping).filter(
            TopicMapping.confidence_score > 0.9
        ).all()

        # Entraîner un modèle de classification
        # Input: (label, keywords, context)
        # Output: master_topic_id
        ...

    def predict_mapping(self, new_topic):
        """Prédit le meilleur master_topic."""
        ...
```

## 🔄 Stratégie de Migration

### Étape 1: Dual-write (Recommandé pour transition)

Pendant une période de transition, écrire dans les **deux** systèmes:

```python
# Lors de l'analyse
with db.transaction():
    # 1. Créer le run_topic (système actuel)
    run_topic = RunTopic(...)
    db.add(run_topic)

    # 2. Vérifier s'il existe un master_topic similaire
    master = find_or_create_master_topic(run_topic)

    # 3. Créer le mapping
    mapping = TopicMapping(
        run_topic_id=run_topic.id,
        master_topic_id=master.id
    )
    db.add(mapping)
```

### Étape 2: Backfill historique

Consolider rétroactivement les runs existants:

```python
def consolidate_historical_runs():
    """
    Consolide tous les runs passés vers master_topics.
    """
    runs = db.query(AnalysisRun).filter(
        AnalysisRun.status == 'success'
    ).all()

    for run in runs:
        for topic in run.topics:
            master = find_or_create_master_topic(topic)
            create_mapping(topic, master)
```

## 📊 Gouvernance des Données

### Règles de gestion recommandées

1. **Immutabilité des runs**
   - Les `run_topics` ne sont JAMAIS modifiés après création
   - Garantit l'auditabilité et la reproductibilité

2. **Versioning des master_topics**
   - Chaque modification crée une nouvelle version
   - Permet de tracker l'évolution des définitions

3. **Workflow de validation**
   - Mappings automatiques marqués comme "pending"
   - Validation manuelle obligatoire pour consolidation
   - Seuil de confiance configurable (ex: 0.85)

4. **Rétention des données**
   - Runs > 6 mois: archiver mais garder les mappings
   - Master_topics orphelins (usage_count=0): review mensuel

## 🆚 Topics Projet vs Entités GIDA

### Différence conceptuelle

| Aspect | Topics Projet (générés LLM) | Entités GIDA (référentiel) |
|--------|----------------------------|---------------------------|
| **Source** | Découverts par LLM dans verbatims | Pré-définis par département GIDA |
| **Évolution** | Émergent organiquement | Gouvernance centralisée |
| **Granularité** | Variable selon le contexte | Standardisée |
| **Usage** | Analyse exploratoire | Quantification standardisée |
| **Exemple** | "Packaging pratique" | "Doliprane" (marque GIDA) |

### Complémentarité

Les deux systèmes coexistent et se complètent:

```
Verbatim: "Le nouveau packaging du Doliprane est très pratique"

Topics détectés:
├── "Packaging pratique" (Topic projet, généré par LLM)
└── Quantifié avec ontologie locale

Entités GIDA détectées:
├── brand: "Doliprane" (Entité GIDA fixe)
└── Quantifié avec keywords GIDA (version 2026.01)
```

## 🎯 Recommandation pour votre cas d'usage

### Court terme (3-6 mois) - MVP actuel

✅ **Garder l'isolation par run**
- Simple, robuste, auditable
- Pas de complexité additionnelle
- Permet de tester et valider le système

**Actions:**
- Ajouter une vue SQL pour détecter les doublons:
  ```sql
  SELECT canonical_label, COUNT(*) as occurrences
  FROM run_topics
  GROUP BY canonical_label
  HAVING COUNT(*) > 3
  ORDER BY occurrences DESC;
  ```
- Exporter régulièrement les topics récurrents pour analyse manuelle

### Moyen terme (6-12 mois) - Consolidation manuelle

✅ **Implémenter Phase 1: master_topics + mappings**
- Interface UI pour consolider
- Fuzzy matching pour suggestions
- Validation manuelle obligatoire

**Actions:**
- Créer tables `master_topics` et `topic_mappings`
- Ajouter page Streamlit "Consolidation"
- Script de backfill pour historique

### Long terme (12+ mois) - Automation

✅ **Implémenter Phase 2-3: Recommandations automatiques**
- LLM pour suggérer mappings
- Apprentissage des patterns
- Consolidation semi-automatique

**Actions:**
- Fine-tuner un modèle sur vos données
- Pipeline MLOps pour recyclage
- Monitoring de la qualité des mappings

## 📝 Exemple de Code: Détection de Doublons

```python
# Script utilitaire pour identifier les topics similaires
from src.db.connection import get_db
from src.db.models import RunTopic
from rapidfuzz import fuzz
from collections import defaultdict

def find_duplicate_topics(threshold: float = 0.85):
    """
    Identifie les topics potentiellement dupliqués.
    """
    with get_db() as db:
        topics = db.query(RunTopic).all()

    # Grouper par similarité
    groups = defaultdict(list)

    for i, topic1 in enumerate(topics):
        for topic2 in topics[i+1:]:
            similarity = fuzz.ratio(
                topic1.canonical_label,
                topic2.canonical_label
            ) / 100.0

            if similarity > threshold:
                groups[topic1.canonical_label].append({
                    'similar_to': topic2.canonical_label,
                    'similarity': similarity,
                    'run_id': topic2.run_id
                })

    # Afficher les groupes
    for canonical, similars in groups.items():
        if similars:
            print(f"\n🔄 '{canonical}' has {len(similars)} similar topics:")
            for s in similars:
                print(f"   - '{s['similar_to']}' ({s['similarity']:.2%})")

if __name__ == "__main__":
    find_duplicate_topics()
```

## 💡 Conclusion

Pour le MVP, **l'isolation par run est la bonne approche**:
- Simple et robuste
- Pas de complexité prématurée
- Permet de valider le système

Une fois le MVP validé et utilisé en production pendant quelques mois, vous aurez assez de données pour:
1. Identifier les patterns de duplication réels
2. Comprendre comment les analystes utilisent les topics
3. Dimensionner correctement la solution de consolidation

**Ne sur-engineerez pas prématurément** - l'architecture actuelle est bien pour démarrer! 🚀

---

*Document créé: 2026-01-22*
