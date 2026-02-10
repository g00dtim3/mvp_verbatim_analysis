"""
Module d'analyse LLM par chunk.
"""

import json
from typing import List, Dict, Optional
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential

from src.llm.client import call_llm_json, count_tokens, estimate_cost
from src.llm.prompts import build_analysis_messages
from src.utils.config import settings


class ChunkAnalyzer:
    """Analyseur de chunks de verbatims."""

    def __init__(
        self,
        brief: str,
        model: str = None,
        timeout: int = None,
        max_retries: int = None
    ):
        """
        Initialise l'analyseur.

        Args:
            brief: Contexte d'analyse fourni par l'analyste
            model: Modèle LLM à utiliser
            timeout: Timeout par appel
            max_retries: Nombre max de retries
        """
        self.brief = brief
        self.model = model or settings.openai_model
        self.timeout = timeout or settings.llm_timeout
        self.max_retries = max_retries or settings.llm_max_retries

        logger.info(f"ChunkAnalyzer initialisé: model={self.model}, brief={len(brief)} chars")

    def analyze_chunk(
        self,
        chunk_index: int,
        verbatims: List[str]
    ) -> Dict:
        """
        Analyse un chunk de verbatims.

        Args:
            chunk_index: Index du chunk
            verbatims: Liste de verbatims du chunk

        Returns:
            {
                'chunk_index': int,
                'status': 'success' | 'failed',
                'themes': [...],
                'summary': str,
                'tokens_used': int,
                'cost': float,
                'error': str (si failed)
            }
        """
        logger.info(f"Analyse chunk {chunk_index} ({len(verbatims)} verbatims)...")

        try:
            # Construire les messages
            messages = build_analysis_messages(self.brief, verbatims)

            # Appeler le LLM
            result = call_llm_json(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=4000,
                timeout=self.timeout
            )

            # Parser le JSON
            if result.get('content_json') is None:
                raise ValueError(f"Réponse JSON invalide: {result.get('json_error')}")

            content = result['content_json']
            themes = content.get('themes', [])

            logger.info(f"✅ Chunk {chunk_index}: {len(themes)} thèmes détectés")

            return {
                'chunk_index': chunk_index,
                'status': 'success',
                'themes': themes,
                'summary': content.get('summary', ''),
                'tokens_used': result['tokens_input'] + result['tokens_output'],
                'cost': result['cost'],
            }

        except Exception as e:
            logger.error(f"❌ Erreur chunk {chunk_index}: {e}")
            return {
                'chunk_index': chunk_index,
                'status': 'failed',
                'error': str(e),
            }

    def analyze_chunks_parallel(
        self,
        chunks: List[List[str]],
        max_workers: int = None
    ) -> List[Dict]:
        """
        Analyse plusieurs chunks en parallèle.

        Args:
            chunks: Liste de chunks (chaque chunk = liste de verbatims)
            max_workers: Nombre de workers parallèles

        Returns:
            Liste de résultats d'analyse
        """
        max_workers = max_workers or settings.llm_parallel_calls

        logger.info(f"Analyse de {len(chunks)} chunks avec {max_workers} workers...")

        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Soumettre les tâches
            futures = {
                executor.submit(self.analyze_chunk, i, chunk): i
                for i, chunk in enumerate(chunks)
            }

            # Récupérer les résultats
            for future in as_completed(futures):
                chunk_idx = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Exception lors de l'analyse du chunk {chunk_idx}: {e}")
                    results.append({
                        'chunk_index': chunk_idx,
                        'status': 'failed',
                        'error': str(e)
                    })

        # Trier par chunk_index
        results.sort(key=lambda x: x['chunk_index'])

        # Stats
        success_count = sum(1 for r in results if r['status'] == 'success')
        failed_count = len(results) - success_count

        logger.info(f"✅ Analyse parallèle terminée: {success_count} succès, {failed_count} échecs")

        return results


def create_chunks(
    verbatims: List[str],
    chunk_size: int = None
) -> List[List[str]]:
    """
    Découpe une liste de verbatims en chunks.

    Args:
        verbatims: Liste de verbatims
        chunk_size: Taille des chunks

    Returns:
        Liste de chunks
    """
    chunk_size = chunk_size or settings.chunk_size

    chunks = []
    for i in range(0, len(verbatims), chunk_size):
        chunk = verbatims[i:i + chunk_size]
        chunks.append(chunk)

    logger.info(f"✅ {len(verbatims)} verbatims découpés en {len(chunks)} chunks de {chunk_size}")
    return chunks


def estimate_analysis_cost(
    verbatims: List[str],
    brief: str,
    chunk_size: int = None,
    model: str = None
) -> Dict:
    """
    Estime le coût et le temps d'une analyse complète.

    Args:
        verbatims: Liste de verbatims
        brief: Contexte d'analyse
        chunk_size: Taille des chunks
        model: Modèle LLM

    Returns:
        {
            'nb_verbatims': int,
            'nb_chunks': int,
            'estimated_tokens_input': int,
            'estimated_tokens_output': int,
            'estimated_cost_usd': float,
            'estimated_time_seconds': int,
        }
    """
    chunk_size = chunk_size or settings.chunk_size
    model = model or settings.openai_model

    # Créer les chunks
    chunks = create_chunks(verbatims, chunk_size)
    nb_chunks = len(chunks)

    # Estimer tokens pour 1 chunk moyen
    sample_chunk = chunks[0] if chunks else []
    sample_messages = build_analysis_messages(brief, sample_chunk)
    sample_prompt = "\n".join([m['content'] for m in sample_messages])

    tokens_input_per_chunk = count_tokens(sample_prompt, model)
    tokens_output_per_chunk = 2000  # Estimation (réponse JSON avec thèmes)

    # Totaux
    total_tokens_input = tokens_input_per_chunk * nb_chunks
    total_tokens_output = tokens_output_per_chunk * nb_chunks

    # Coût
    total_cost = estimate_cost(total_tokens_input, total_tokens_output, model)

    # Temps (estimation: 30s par chunk en moyenne, avec parallélisme)
    time_per_chunk = 30  # secondes
    parallelism = settings.llm_parallel_calls
    estimated_time = (nb_chunks * time_per_chunk) / parallelism

    return {
        'nb_verbatims': len(verbatims),
        'nb_chunks': nb_chunks,
        'estimated_tokens_input': total_tokens_input,
        'estimated_tokens_output': total_tokens_output,
        'estimated_cost_usd': total_cost,
        'estimated_time_seconds': int(estimated_time),
    }


def check_cost_alerts(nb_chunks: int) -> Dict:
    """
    Vérifie si des alertes de coût doivent être levées.

    Args:
        nb_chunks: Nombre de chunks

    Returns:
        {
            'alert_level': 'none' | 'warning' | 'blocking',
            'message': str,
            'nb_chunks': int,
        }
    """
    if nb_chunks >= settings.chunk_blocking_threshold:
        return {
            'alert_level': 'blocking',
            'message': (
                f"⛔ Blocage: {nb_chunks} chunks (max: {settings.chunk_blocking_threshold}). "
                f"Dataset trop large pour le mode complet. Utilisez le mode rapide."
            ),
            'nb_chunks': nb_chunks,
        }

    if nb_chunks >= settings.chunk_warning_threshold:
        return {
            'alert_level': 'warning',
            'message': (
                f"⚠️ Attention: {nb_chunks} chunks détectés (warning à {settings.chunk_warning_threshold}). "
                f"Coût estimé élevé. Confirmez avant de continuer."
            ),
            'nb_chunks': nb_chunks,
        }

    return {
        'alert_level': 'none',
        'message': f"✅ {nb_chunks} chunks, aucune alerte",
        'nb_chunks': nb_chunks,
    }


def extract_all_themes_from_results(
    chunk_results: List[Dict]
) -> List[Dict]:
    """
    Extrait tous les thèmes de tous les chunks réussis.

    Args:
        chunk_results: Résultats d'analyse des chunks

    Returns:
        Liste de thèmes avec métadonnées
    """
    all_themes = []

    for result in chunk_results:
        if result['status'] != 'success':
            continue

        chunk_idx = result['chunk_index']
        themes = result.get('themes', [])

        for theme in themes:
            all_themes.append({
                'chunk_index': chunk_idx,
                'topic_label': theme.get('topic_label', ''),
                'subtopic_label': theme.get('subtopic_label'),
                'pain_points': theme.get('pain_points', []),
                'benefits': theme.get('benefits', []),
                'usage_context': theme.get('usage_context', ''),
                'example_verbatims': theme.get('example_verbatims', []),
            })

    logger.info(f"✅ {len(all_themes)} thèmes extraits de {len(chunk_results)} chunks")
    return all_themes
