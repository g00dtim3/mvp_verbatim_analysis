"""
Module de quantification Python déterministe.
"""

import re
from typing import List, Dict, Set, Optional, Tuple
from loguru import logger
from collections import defaultdict

from src.utils.config import settings


def match_keywords_in_text(
    text: str,
    keywords: List[str],
    negative_keywords: List[str] = None,
    negation_patterns: List[str] = None,
    regex_patterns: List[str] = None
) -> List[str]:
    """
    Détecte les keywords dans un texte avec gestion des négations.

    Args:
        text: Texte à analyser
        keywords: Liste de keywords à détecter
        negative_keywords: Keywords à exclure
        negation_patterns: Patterns de négation
        regex_patterns: Patterns regex optionnels

    Returns:
        Liste des keywords matchés (distincts)
    """
    if not text:
        return []

    text_lower = text.lower()
    matched = set()

    negative_keywords = negative_keywords or []
    negation_patterns = negation_patterns or []

    # 1. Vérifier les negative keywords (exclusion globale)
    for neg_kw in negative_keywords:
        if neg_kw.lower() in text_lower:
            # logger.debug(f"Negative keyword détecté: {neg_kw}")
            return []  # Exclusion totale

    # 2. Matcher les keywords
    for kw in keywords:
        kw_lower = kw.lower()

        # Vérifier présence
        if kw_lower not in text_lower:
            continue

        # Vérifier négation
        if _is_negated(text_lower, kw_lower, negation_patterns):
            # logger.debug(f"Keyword négation détectée: {kw}")
            continue

        matched.add(kw)

    # 3. Matcher les regex (optionnel)
    if regex_patterns:
        for pattern in regex_patterns:
            try:
                if re.search(pattern, text_lower):
                    matched.add(f"[regex:{pattern[:20]}]")
            except re.error as e:
                logger.warning(f"Regex invalide: {pattern} - {e}")

    return list(matched)


def _is_negated(
    text: str,
    keyword: str,
    negation_patterns: List[str],
    window: int = None
) -> bool:
    """
    Vérifie si un keyword est dans une fenêtre de négation.

    Args:
        text: Texte complet (lowercase)
        keyword: Keyword à vérifier (lowercase)
        negation_patterns: Patterns de négation
        window: Fenêtre en nombre de mots (défaut: settings.negation_window)

    Returns:
        True si le keyword est négation
    """
    window = window or settings.negation_window

    # Trouver toutes les positions du keyword
    positions = [m.start() for m in re.finditer(re.escape(keyword), text)]

    for pos in positions:
        # Extraire le contexte avant le keyword (N mots)
        context_start = max(0, pos - (window * 10))  # Approximation: 10 chars par mot
        context = text[context_start:pos]

        # Vérifier si un pattern de négation est présent
        for neg_pattern in negation_patterns:
            if neg_pattern in context:
                return True

    return False


def quantify_topics(
    verbatims: List[str],
    topics_with_ontology: List[Dict]
) -> List[Dict]:
    """
    Quantifie tous les thèmes sur les verbatims.

    Args:
        verbatims: Liste de verbatims (clean)
        topics_with_ontology: Liste de {topic, ontology}

    Returns:
        Liste de {topic, metrics}
    """
    logger.info(f"Quantification de {len(topics_with_ontology)} thèmes sur {len(verbatims)} verbatims...")

    results = []

    for item in topics_with_ontology:
        topic = item['topic']
        ontology = item['ontology']

        metrics = _quantify_single_topic(verbatims, ontology)

        results.append({
            'topic': topic,
            'ontology': ontology,
            'metrics': metrics
        })

    logger.info("✅ Quantification terminée")
    return results


def _quantify_single_topic(
    verbatims: List[str],
    ontology: Dict
) -> Dict:
    """
    Quantifie un seul thème.

    Args:
        verbatims: Liste de verbatims
        ontology: Ontologie du thème

    Returns:
        {
            'volume_verbatims': int,
            'volume_mentions': int,
            'pct_of_dataset': float,
            'matched_verbatim_indices': [...],
            'keyword_counts': {...}
        }
    """
    keywords = ontology.get('keywords', [])
    negative_keywords = ontology.get('negative_keywords', [])
    negation_patterns = ontology.get('negation_patterns', [])
    regex_patterns = ontology.get('regex_patterns', [])

    matched_verbatim_indices = []
    all_keywords_matched = []

    for i, verbatim in enumerate(verbatims):
        matched_kw = match_keywords_in_text(
            text=verbatim,
            keywords=keywords,
            negative_keywords=negative_keywords,
            negation_patterns=negation_patterns,
            regex_patterns=regex_patterns
        )

        if matched_kw:
            matched_verbatim_indices.append(i)
            all_keywords_matched.extend(matched_kw)

    # Métriques
    volume_verbatims = len(matched_verbatim_indices)
    volume_mentions = len(set(all_keywords_matched))  # Nombre de keywords distincts
    pct_of_dataset = (volume_verbatims / len(verbatims) * 100) if verbatims else 0

    # Compter par keyword
    keyword_counts = {}
    for kw in all_keywords_matched:
        keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

    return {
        'volume_verbatims': volume_verbatims,
        'volume_mentions': volume_mentions,
        'pct_of_dataset': round(pct_of_dataset, 2),
        'matched_verbatim_indices': matched_verbatim_indices,
        'keyword_counts': keyword_counts,
    }


def quantify_entities_gida(
    verbatims: List[str],
    gida_entities: List[Dict]
) -> Dict:
    """
    Quantifie les entités GIDA (pathologies, marques, zones, attributs).

    Args:
        verbatims: Liste de verbatims
        gida_entities: Liste d'entités GIDA
            Chaque entité: {entity_type, label, keywords}

    Returns:
        {
            'entity_type': {
                'entity_label': {
                    'volume_verbatims': int,
                    'matched_verbatim_indices': [...]
                }
            }
        }
    """
    logger.info(f"Quantification GIDA: {len(gida_entities)} entités sur {len(verbatims)} verbatims...")

    results = defaultdict(lambda: defaultdict(dict))

    for entity in gida_entities:
        entity_type = entity.get('entity_type', 'unknown')
        entity_label = entity.get('label', '')
        keywords = entity.get('keywords', [])

        matched_indices = []

        for i, verbatim in enumerate(verbatims):
            matched = match_keywords_in_text(
                text=verbatim,
                keywords=keywords
            )

            if matched:
                matched_indices.append(i)

        results[entity_type][entity_label] = {
            'volume_verbatims': len(matched_indices),
            'matched_verbatim_indices': matched_indices,
        }

    logger.info("✅ Quantification GIDA terminée")
    return dict(results)


def create_enriched_dataframe(
    verbatims: List[str],
    topics_quantified: List[Dict],
    entities_quantified: Dict = None
) -> List[Dict]:
    """
    Crée un dataset enrichi avec colonnes de thèmes et entités.

    Args:
        verbatims: Liste de verbatims
        topics_quantified: Résultats de quantification des thèmes
        entities_quantified: Résultats de quantification GIDA

    Returns:
        Liste de dicts (chaque dict = 1 verbatim enrichi)
    """
    logger.info("Création du dataset enrichi...")

    enriched = []

    for i, verbatim in enumerate(verbatims):
        row = {
            'verbatim_index': i,
            'full_text': verbatim,
            'topics': [],
            'entities': {},
        }

        # Ajouter les thèmes
        for item in topics_quantified:
            topic = item['topic']
            metrics = item['metrics']

            if i in metrics['matched_verbatim_indices']:
                row['topics'].append(topic.get('canonical_label', ''))

        # Ajouter les entités GIDA
        if entities_quantified:
            for entity_type, entities in entities_quantified.items():
                row['entities'][entity_type] = []
                for entity_label, data in entities.items():
                    if i in data['matched_verbatim_indices']:
                        row['entities'][entity_type].append(entity_label)

        enriched.append(row)

    logger.info(f"✅ Dataset enrichi créé: {len(enriched)} lignes")
    return enriched


def get_quantification_summary(
    topics_quantified: List[Dict]
) -> Dict:
    """
    Génère un résumé de la quantification.

    Args:
        topics_quantified: Résultats de quantification

    Returns:
        Dictionnaire de stats
    """
    total_topics = len(topics_quantified)
    topics_with_matches = sum(
        1 for item in topics_quantified
        if item['metrics']['volume_verbatims'] > 0
    )

    # Top thèmes par volume
    top_topics = sorted(
        topics_quantified,
        key=lambda x: x['metrics']['volume_verbatims'],
        reverse=True
    )[:10]

    return {
        'total_topics': total_topics,
        'topics_with_matches': topics_with_matches,
        'topics_without_matches': total_topics - topics_with_matches,
        'top_topics': [
            {
                'label': item['topic'].get('canonical_label', ''),
                'volume': item['metrics']['volume_verbatims'],
                'pct': item['metrics']['pct_of_dataset']
            }
            for item in top_topics
        ]
    }
