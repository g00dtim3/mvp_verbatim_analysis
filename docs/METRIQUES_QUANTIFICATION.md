# Métriques de Quantification

## Vue d'ensemble

La quantification calcule automatiquement 3 métriques principales pour chaque thème identifié lors de l'analyse.

## Métriques

### 1. Volume (verbatims)

**Définition**: Nombre de verbatims (avis/commentaires) uniques qui mentionnent ce thème **au moins une fois**.

**Exemple**:
- Si 45 clients différents parlent d'efficacité dans leurs avis
- **Volume (verbatims) = 45**

**Utilité**:
- Mesure la **popularité** du thème
- Indique combien de personnes abordent ce sujet
- Permet de prioriser les thèmes selon leur importance

**Formule**: `COUNT(DISTINCT verbatim_id WHERE theme_matched)`

---

### 2. Volume (mentions)

**Définition**: Nombre de keywords **distincts** de ce thème qui ont été effectivement trouvés dans l'ensemble du dataset.

**Exemple**:
Le thème "Efficacité du produit" a 10 keywords possibles générés par le LLM:
- "efficacité"
- "résultats"
- "efficace"
- "fonctionne bien"
- "amélioration"
- "effet visible"
- "performant"
- "actif"
- "impact"
- "bénéfices"

Si dans les 45 verbatims, seulement **3 de ces keywords** sont réellement utilisés:
- "efficacité" (trouvé dans 20 verbatims)
- "résultats" (trouvé dans 15 verbatims)
- "amélioration" (trouvé dans 10 verbatims)

Alors **Volume (mentions) = 3** (nombre de keywords distincts trouvés)

**Utilité**:
- Mesure la **diversité lexicale** du thème
- Indique la richesse du vocabulaire utilisé par les clients
- Aide à évaluer la qualité de l'ontologie générée

---

### 3. % Dataset

**Définition**: Pourcentage de verbatims du dataset qui mentionnent ce thème.

**Formule**: `(Volume verbatims / Total verbatims) × 100`

**Exemple**:
- Dataset total: 300 verbatims
- Volume verbatims pour "Efficacité": 45
- **% Dataset = 15.0%**

**Utilité**:
- Permet la **comparaison** entre datasets de tailles différentes
- Facilite le benchmarking entre analyses
- Donne une vue rapide de l'importance relative

---

## Interprétation combinée

### Cas 1: Volume élevé, Mentions faibles
```
Volume (verbatims) = 80
Volume (mentions) = 2
% Dataset = 26.7%
```

**Interprétation**:
- Thème très populaire (26.7% du dataset)
- Mais vocabulaire très limité (2 mots différents seulement)
- Les clients utilisent toujours les mêmes termes
- L'ontologie pourrait être enrichie

**Action recommandée**: Examiner les verbatims pour identifier d'autres façons d'exprimer ce thème

---

### Cas 2: Volume élevé, Mentions élevées
```
Volume (verbatims) = 80
Volume (mentions) = 12
% Dataset = 26.7%
```

**Interprétation**:
- Thème très populaire (26.7%)
- Vocabulaire riche et varié (12 mots différents)
- Les clients s'expriment de façons diverses
- L'ontologie capture bien la variété

**Action recommandée**: Analyser les nuances sémantiques entre les différents keywords

---

### Cas 3: Volume faible, Mentions faibles
```
Volume (verbatims) = 5
Volume (mentions) = 1
% Dataset = 1.7%
```

**Interprétation**:
- Thème minoritaire (1.7%)
- Vocabulaire très limité (1 seul mot)
- Peut être un thème émergent ou très spécifique
- Pourrait être fusionné avec un thème similaire

**Action recommandée**: Vérifier la pertinence du thème et envisager une fusion

---

### Cas 4: Volume faible, Mentions élevées
```
Volume (verbatims) = 5
Volume (mentions) = 8
% Dataset = 1.7%
```

**Interprétation**:
- Thème minoritaire (1.7%)
- Mais vocabulaire riche (8 mots pour 5 verbatims)
- Les quelques personnes qui en parlent utilisent beaucoup de termes différents
- **ALERTE**: Possible sur-génération de keywords par le LLM

**Action recommandée**:
- Vérifier la qualité de l'ontologie
- Certains keywords sont peut-être des faux positifs
- Affiner les keywords négatifs pour réduire le bruit

---

## Calcul technique

Le calcul se fait dans `src/api/quantification.py`:

```python
def _quantify_single_topic(verbatims, ontology):
    keywords = ontology['keywords']
    matched_verbatim_indices = []
    all_keywords_matched = []

    for i, verbatim in enumerate(verbatims):
        matched_kw = match_keywords_in_text(
            text=verbatim,
            keywords=keywords,
            negative_keywords=ontology['negative_keywords'],
            negation_patterns=ontology['negation_patterns']
        )

        if matched_kw:
            matched_verbatim_indices.append(i)
            all_keywords_matched.extend(matched_kw)

    return {
        'volume_verbatims': len(matched_verbatim_indices),  # Verbatims uniques
        'volume_mentions': len(set(all_keywords_matched)),  # Keywords distincts
        'pct_of_dataset': (len(matched_verbatim_indices) / len(verbatims)) * 100
    }
```

---

## Exemples réels

### Thème: "Texture et Absorption"
```
Volume (verbatims) = 42
Volume (mentions) = 6
% Dataset = 14.0%

Keywords trouvés:
1. "texture" (dans 25 verbatims)
2. "absorption" (dans 18 verbatims)
3. "pénètre bien" (dans 12 verbatims)
4. "légère" (dans 8 verbatims)
5. "fluide" (dans 5 verbatims)
6. "ne colle pas" (dans 3 verbatims)
```

**Analyse**:
- 14% des clients mentionnent la texture/absorption
- 6 façons différentes d'en parler
- Vocabulaire moyennement diversifié
- Bonne couverture du concept

---

### Thème: "Prix élevé"
```
Volume (verbatims) = 67
Volume (mentions) = 2
% Dataset = 22.3%

Keywords trouvés:
1. "cher" (dans 50 verbatims)
2. "prix" (dans 40 verbatims)
```

**Analyse**:
- 22.3% se plaignent du prix (thème majeur!)
- Mais seulement 2 mots utilisés
- Vocabulaire très pauvre
- **Action**: Chercher d'autres formulations ("coûteux", "onéreux", "budget", "rapport qualité-prix", etc.)

---

## FAQ

**Q: Pourquoi Volume (mentions) peut être > Volume (verbatims)?**

R: C'est **impossible**. Volume (mentions) ≤ nombre total de keywords dans l'ontologie, et en pratique Volume (mentions) ≤ Volume (verbatims) car chaque verbatim utilise au max tous les keywords.

**Q: Que signifie Volume (mentions) = 0 mais Volume (verbatims) = 10?**

R: **Erreur de calcul**. Si 10 verbatims matchent, au moins 1 keyword doit avoir matché. Cela indiquerait un bug.

**Q: Comment améliorer Volume (mentions) si trop faible?**

R:
1. Examiner manuellement les verbatims qui matchent
2. Identifier les synonymes et expressions alternatives
3. Ajouter ces termes aux keywords de l'ontologie
4. Re-quantifier (fonctionnalité future)

**Q: Faut-il toujours viser un Volume (mentions) élevé?**

R: Non. Un thème peut légitimement n'avoir qu'un seul mot-clé courant. L'important est que tous les verbatims pertinents soient capturés, pas nécessairement avec beaucoup de keywords différents.
