"""
Prompts pour l'analyse thématique par LLM.
"""

# ===========================================
# ANALYSE THÉMATIQUE
# ===========================================

SYSTEM_PROMPT_ANALYSIS = """Tu es un expert en analyse qualitative de verbatims consommateurs.
Tu analyses des données issues de réseaux sociaux et d'avis clients.
Tu dois identifier les thèmes principaux, sous-thèmes, pain points et bénéfices attendus.

Règles:
- Sois précis et factuel
- Base-toi uniquement sur les verbatims fournis
- Identifie les nuances de sentiment
- Regroupe les thèmes de manière cohérente
- Fournis des exemples de verbatims pour illustrer chaque thème
"""

PROMPT_ANALYZE_VERBATIMS = """
## Contexte de l'analyse
{brief}

## Verbatims à analyser
{verbatims}

## Instructions
Analyse ces verbatims et identifie les thèmes principaux.

Pour chaque thème, fournis:
1. **Thème principal** (label court et clair)
2. **Sous-thème** (si pertinent)
3. **Pain points** (problèmes/frustrations exprimés)
4. **Bénéfices attendus** (ce que les consommateurs recherchent)
5. **Contexte d'usage** (quand/comment le produit est utilisé)
6. **Exemples** (2-3 verbatims représentatifs, copiés exactement)

## Format de sortie (JSON)
{{
  "themes": [
    {{
      "topic_label": "string",
      "subtopic_label": "string ou null",
      "pain_points": ["string"],
      "benefits": ["string"],
      "usage_context": "string",
      "example_verbatims": ["string"]
    }}
  ],
  "summary": "string (résumé en 2-3 phrases)"
}}
"""


# ===========================================
# FUSION DES THÈMES
# ===========================================

SYSTEM_PROMPT_MERGE = """Tu es un expert en taxonomie et classification.
Tu dois déterminer si des labels de thèmes représentent le même concept ou des concepts distincts.
Sois rigoureux: deux thèmes proches mais avec une nuance importante doivent rester séparés.
"""

PROMPT_MERGE_TOPICS = """
## Contexte
Ces labels de thèmes ont été extraits de différents sous-ensembles d'un même dataset de verbatims.
Certains peuvent représenter le même concept avec des formulations différentes.

## Labels à évaluer
{topic_labels}

## Instructions
Pour chaque groupe de labels similaires:
1. Détermine s'ils représentent le MÊME concept
2. Si oui, propose un label canonique (le plus clair et représentatif)
3. Liste les alias (autres formulations)
4. Justifie brièvement ta décision

Si des labels sont distincts, ne les fusionne PAS.

## Format de sortie (JSON)
{{
  "merge_groups": [
    {{
      "canonical_label": "string",
      "aliases": ["string"],
      "rationale": "string"
    }}
  ],
  "distinct_labels": ["string (labels qui ne fusionnent avec aucun autre)"]
}}
"""


# ===========================================
# GÉNÉRATION ONTOLOGIE PROJET
# ===========================================

SYSTEM_PROMPT_ONTOLOGY = """Tu es un expert en NLP et extraction d'information.
Tu dois générer des règles de matching (keywords, regex) pour détecter des thèmes dans du texte.
Les règles doivent être précises pour éviter les faux positifs.
"""

PROMPT_GENERATE_KEYWORDS = """
## Thème à modéliser
- Label: {topic_label}
- Sous-thème: {subtopic_label}
- Description: {description}
- Exemples de verbatims:
{example_verbatims}

## Instructions
Génère des règles de matching pour détecter ce thème dans des verbatims.

1. **Keywords**: mots ou expressions qui indiquent ce thème
   - Inclus les variantes (singulier/pluriel, synonymes)
   - Inclus les fautes d'orthographe courantes si pertinent
   
2. **Negative keywords**: mots qui, s'ils sont présents, indiquent un FAUX POSITIF
   - Ex: pour "livraison rapide", "pas rapide" serait un négatif
   
3. **Regex patterns** (optionnel): pour des cas complexes
   - Utilise une syntaxe Python regex

## Format de sortie (JSON)
{{
  "keywords": ["string"],
  "negative_keywords": ["string"],
  "regex_patterns": ["string (optionnel)"],
  "confidence_notes": "string (notes sur la fiabilité des règles)"
}}
"""


# ===========================================
# HELPERS
# ===========================================

def format_verbatims_for_prompt(verbatims: list[str], max_chars: int = 50000) -> str:
    """
    Formate une liste de verbatims pour inclusion dans un prompt.
    
    Args:
        verbatims: Liste de textes
        max_chars: Limite de caractères
        
    Returns:
        Texte formaté avec numérotation
    """
    formatted = []
    total_chars = 0
    
    for i, v in enumerate(verbatims, 1):
        line = f"[{i}] {v}"
        if total_chars + len(line) > max_chars:
            formatted.append(f"... ({len(verbatims) - i + 1} verbatims tronqués)")
            break
        formatted.append(line)
        total_chars += len(line) + 1
    
    return "\n".join(formatted)


def format_topics_for_merge(topics: list[dict]) -> str:
    """
    Formate une liste de thèmes pour le prompt de fusion.
    
    Args:
        topics: Liste de dicts avec 'topic_label' et optionnel 'subtopic_label'
        
    Returns:
        Texte formaté
    """
    lines = []
    for i, t in enumerate(topics, 1):
        label = t.get('topic_label', '')
        subtopic = t.get('subtopic_label', '')
        if subtopic:
            lines.append(f"{i}. {label} > {subtopic}")
        else:
            lines.append(f"{i}. {label}")
    
    return "\n".join(lines)


def build_analysis_messages(brief: str, verbatims: list[str]) -> list[dict]:
    """
    Construit les messages pour l'analyse thématique.
    
    Returns:
        Liste de messages pour l'API OpenAI
    """
    verbatims_text = format_verbatims_for_prompt(verbatims)
    
    user_prompt = PROMPT_ANALYZE_VERBATIMS.format(
        brief=brief or "Analyse générale des verbatims",
        verbatims=verbatims_text
    )
    
    return [
        {"role": "system", "content": SYSTEM_PROMPT_ANALYSIS},
        {"role": "user", "content": user_prompt}
    ]


def build_merge_messages(topics: list[dict]) -> list[dict]:
    """
    Construit les messages pour la fusion des thèmes.
    
    Returns:
        Liste de messages pour l'API OpenAI
    """
    topics_text = format_topics_for_merge(topics)
    
    user_prompt = PROMPT_MERGE_TOPICS.format(topic_labels=topics_text)
    
    return [
        {"role": "system", "content": SYSTEM_PROMPT_MERGE},
        {"role": "user", "content": user_prompt}
    ]


def build_ontology_messages(
    topic_label: str,
    subtopic_label: str = None,
    description: str = None,
    example_verbatims: list[str] = None
) -> list[dict]:
    """
    Construit les messages pour la génération d'ontologie.
    
    Returns:
        Liste de messages pour l'API OpenAI
    """
    examples_text = "\n".join(
        f"- {v}" for v in (example_verbatims or [])[:5]
    ) or "Aucun exemple fourni"
    
    user_prompt = PROMPT_GENERATE_KEYWORDS.format(
        topic_label=topic_label,
        subtopic_label=subtopic_label or "N/A",
        description=description or "Pas de description",
        example_verbatims=examples_text
    )
    
    return [
        {"role": "system", "content": SYSTEM_PROMPT_ONTOLOGY},
        {"role": "user", "content": user_prompt}
    ]
