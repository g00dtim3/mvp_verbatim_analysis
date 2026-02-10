"""
Module de génération d'ontologie projet (keywords/regex pour quantification).
"""

from typing import List, Dict, Optional
from loguru import logger
import json

from src.llm.client import call_llm_json
from src.llm.prompts import build_ontology_messages
from src.utils.config import DEFAULT_NEGATION_PATTERNS


class OntologyGenerator:
    """Générateur d'ontologie projet."""

    def __init__(self, model: str = None):
        """
        Initialise le générateur.

        Args:
            model: Modèle LLM à utiliser
        """
        self.model = model
        logger.info("OntologyGenerator initialisé")

    def generate_for_topic(
        self,
        topic_label: str,
        subtopic_label: Optional[str] = None,
        pain_points: List[str] = None,
        benefits: List[str] = None,
        usage_context: str = None,
        example_verbatims: List[str] = None
    ) -> Dict:
        """
        Génère l'ontologie (keywords/regex) pour un thème donné.

        Args:
            topic_label: Label du thème
            subtopic_label: Sous-thème (optionnel)
            pain_points: Liste de pain points
            benefits: Liste de bénéfices
            usage_context: Contexte d'usage
            example_verbatims: Exemples de verbatims

        Returns:
            {
                'keywords': [...],
                'regex_patterns': [...],
                'negative_keywords': [...],
                'negation_patterns': [...],
                'confidence_notes': str
            }
        """
        logger.info(f"Génération ontologie pour: {topic_label}")

        # Construire une description du thème
        description_parts = []

        if pain_points:
            description_parts.append(f"Pain points: {', '.join(pain_points[:3])}")

        if benefits:
            description_parts.append(f"Bénéfices: {', '.join(benefits[:3])}")

        if usage_context:
            description_parts.append(f"Contexte: {usage_context}")

        description = " | ".join(description_parts) if description_parts else "Pas de description"

        # Appeler le LLM
        try:
            messages = build_ontology_messages(
                topic_label=topic_label,
                subtopic_label=subtopic_label,
                description=description,
                example_verbatims=example_verbatims or []
            )

            result = call_llm_json(
                messages=messages,
                model=self.model,
                temperature=0.5,
                max_tokens=2000
            )

            if result.get('content_json') is None:
                raise ValueError(f"Réponse JSON invalide: {result.get('json_error')}")

            content = result['content_json']

            # Ajouter les patterns de négation par défaut
            negation_patterns = content.get('negation_patterns', [])
            if not negation_patterns:
                negation_patterns = DEFAULT_NEGATION_PATTERNS

            ontology = {
                'keywords': content.get('keywords', []),
                'regex_patterns': content.get('regex_patterns', []),
                'negative_keywords': content.get('negative_keywords', []),
                'negation_patterns': negation_patterns,
                'confidence_notes': content.get('confidence_notes', ''),
                'llm_cost': result.get('cost', 0),
            }

            logger.info(
                f"✅ Ontologie générée: {len(ontology['keywords'])} keywords, "
                f"{len(ontology['regex_patterns'])} regex"
            )

            return ontology

        except Exception as e:
            logger.error(f"❌ Erreur génération ontologie: {e}")

            # Fallback: Ontologie minimale basée sur le label
            return self._generate_fallback_ontology(topic_label, subtopic_label)

    def _generate_fallback_ontology(
        self,
        topic_label: str,
        subtopic_label: Optional[str] = None
    ) -> Dict:
        """
        Génère une ontologie minimale en fallback (sans LLM).

        Args:
            topic_label: Label du thème
            subtopic_label: Sous-thème

        Returns:
            Ontologie minimale
        """
        logger.warning("Utilisation de l'ontologie fallback (sans LLM)")

        # Extraire des mots simples du label
        keywords = []

        # Ajouter le label complet
        keywords.append(topic_label.lower())

        if subtopic_label:
            keywords.append(subtopic_label.lower())

        # Ajouter les mots individuels (> 3 caractères)
        words = topic_label.split() + (subtopic_label.split() if subtopic_label else [])
        keywords.extend([w.lower() for w in words if len(w) > 3])

        return {
            'keywords': list(set(keywords)),
            'regex_patterns': [],
            'negative_keywords': [],
            'negation_patterns': DEFAULT_NEGATION_PATTERNS,
            'confidence_notes': 'Ontologie générée automatiquement (fallback)',
            'llm_cost': 0,
        }

    def generate_for_all_topics(
        self,
        topics: List[Dict]
    ) -> List[Dict]:
        """
        Génère l'ontologie pour tous les thèmes.

        Args:
            topics: Liste de thèmes fusionnés

        Returns:
            Liste de {topic, ontology}
        """
        logger.info(f"Génération ontologie pour {len(topics)} thèmes...")

        results = []

        for topic in topics:
            ontology = self.generate_for_topic(
                topic_label=topic.get('canonical_label', ''),
                subtopic_label=topic.get('canonical_subtopic'),
                pain_points=topic.get('pain_points', []),
                benefits=topic.get('benefits', []),
                usage_context=topic.get('usage_context'),
                example_verbatims=topic.get('example_verbatims', [])
            )

            results.append({
                'topic': topic,
                'ontology': ontology
            })

        total_cost = sum(r['ontology'].get('llm_cost', 0) for r in results)
        logger.info(f"✅ Ontologie générée pour {len(results)} thèmes (coût: ${total_cost:.4f})")

        return results


def validate_ontology(
    ontology: Dict,
    test_verbatims: List[str]
) -> Dict:
    """
    Valide une ontologie sur un échantillon de verbatims.

    Args:
        ontology: Ontologie à valider
        test_verbatims: Verbatims de test

    Returns:
        {
            'matches': int,
            'match_rate': float,
            'examples': [...]
        }
    """
    from src.api.quantification import match_keywords_in_text

    keywords = ontology.get('keywords', [])
    negative_keywords = ontology.get('negative_keywords', [])
    negation_patterns = ontology.get('negation_patterns', [])

    matches = 0
    examples = []

    for verbatim in test_verbatims[:100]:  # Max 100 pour test
        matched = match_keywords_in_text(
            text=verbatim,
            keywords=keywords,
            negative_keywords=negative_keywords,
            negation_patterns=negation_patterns
        )

        if matched:
            matches += 1
            if len(examples) < 5:
                examples.append({
                    'verbatim': verbatim,
                    'matched_keywords': matched
                })

    match_rate = matches / len(test_verbatims[:100]) if test_verbatims else 0

    return {
        'matches': matches,
        'match_rate': round(match_rate, 3),
        'examples': examples,
    }


def export_ontology_to_json(
    ontology_results: List[Dict],
    filepath: str
) -> bool:
    """
    Exporte l'ontologie projet au format JSON.

    Args:
        ontology_results: Résultats de génération
        filepath: Chemin de sortie

    Returns:
        True si succès
    """
    try:
        output = {
            'topics': []
        }

        for result in ontology_results:
            topic = result['topic']
            ontology = result['ontology']

            output['topics'].append({
                'label': topic.get('canonical_label', ''),
                'sublabel': topic.get('canonical_subtopic'),
                'aliases': topic.get('aliases', []),
                'keywords': ontology.get('keywords', []),
                'regex_patterns': ontology.get('regex_patterns', []),
                'negative_keywords': ontology.get('negative_keywords', []),
                'negation_patterns': ontology.get('negation_patterns', []),
            })

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Ontologie exportée: {filepath}")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur export ontologie: {e}")
        return False
