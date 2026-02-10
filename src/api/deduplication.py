"""
Module de déduplication des verbatims avec fuzzy matching.
"""

from typing import List, Dict, Tuple, Set
from rapidfuzz import fuzz
from loguru import logger
import uuid
from collections import defaultdict


def compute_fuzzy_similarity(text1: str, text2: str) -> float:
    """
    Calcule la similarité fuzzy entre deux textes.

    Args:
        text1: Premier texte
        text2: Deuxième texte

    Returns:
        Score de similarité (0-1)
    """
    # Utiliser le ratio de Levenshtein normalisé
    score = fuzz.ratio(text1, text2) / 100.0
    return score


def find_duplicates(
    texts: List[str],
    threshold: float = 0.90,
    use_indices: bool = False
) -> List[Tuple[int, int, float]]:
    """
    Trouve les paires de textes similaires au-dessus du seuil.

    Args:
        texts: Liste de textes
        threshold: Seuil de similarité (0-1)
        use_indices: Si True, retourne les indices, sinon les IDs

    Returns:
        Liste de (idx1, idx2, score)
    """
    duplicates = []
    n = len(texts)

    logger.info(f"Recherche de doublons (seuil={threshold})...")

    # Pairwise comparison (optimisation possible avec indexation)
    for i in range(n):
        for j in range(i + 1, n):
            score = compute_fuzzy_similarity(texts[i], texts[j])
            if score >= threshold:
                duplicates.append((i, j, score))

    logger.info(f"✅ {len(duplicates)} paires de doublons trouvées")
    return duplicates


def group_duplicates(
    duplicates: List[Tuple[int, int, float]]
) -> List[Set[int]]:
    """
    Regroupe les doublons en clusters (composantes connexes).

    Args:
        duplicates: Liste de (idx1, idx2, score)

    Returns:
        Liste de sets d'indices appartenant au même cluster
    """
    # Graph representation: adjacency list
    graph = defaultdict(set)

    for idx1, idx2, _ in duplicates:
        graph[idx1].add(idx2)
        graph[idx2].add(idx1)

    # Find connected components (DFS)
    visited = set()
    clusters = []

    def dfs(node, cluster):
        visited.add(node)
        cluster.add(node)
        for neighbor in graph[node]:
            if neighbor not in visited:
                dfs(neighbor, cluster)

    all_nodes = set(graph.keys())
    for node in all_nodes:
        if node not in visited:
            cluster = set()
            dfs(node, cluster)
            clusters.append(cluster)

    logger.info(f"✅ {len(clusters)} clusters de doublons créés")
    return clusters


def mark_duplicates_for_removal(
    clusters: List[Set[int]],
    keep_first: bool = True
) -> Set[int]:
    """
    Marque les indices à retirer (garde 1 exemplaire par cluster).

    Args:
        clusters: Clusters de doublons
        keep_first: Si True, garde le premier indice de chaque cluster

    Returns:
        Set d'indices à retirer
    """
    to_remove = set()

    for cluster in clusters:
        sorted_cluster = sorted(cluster)
        if keep_first:
            # Garder le premier, retirer les autres
            to_remove.update(sorted_cluster[1:])
        else:
            # Garder le dernier, retirer les autres
            to_remove.update(sorted_cluster[:-1])

    logger.info(f"✅ {len(to_remove)} verbatims marqués pour suppression")
    return to_remove


def deduplicate_texts(
    texts: List[str],
    threshold: float = 0.90
) -> Tuple[List[str], List[int], Dict]:
    """
    Déduplique une liste de textes.

    Args:
        texts: Liste de textes
        threshold: Seuil de similarité

    Returns:
        (texts_uniques, indices_gardés, stats)
    """
    if len(texts) == 0:
        return [], [], {}

    # 1. Trouver les doublons
    duplicates = find_duplicates(texts, threshold)

    if len(duplicates) == 0:
        # Aucun doublon
        return texts, list(range(len(texts))), {
            'total_before': len(texts),
            'total_after': len(texts),
            'removed': 0,
            'clusters': 0,
        }

    # 2. Grouper en clusters
    clusters = group_duplicates(duplicates)

    # 3. Marquer pour suppression
    to_remove = mark_duplicates_for_removal(clusters)

    # 4. Filtrer
    texts_unique = [t for i, t in enumerate(texts) if i not in to_remove]
    indices_kept = [i for i in range(len(texts)) if i not in to_remove]

    stats = {
        'total_before': len(texts),
        'total_after': len(texts_unique),
        'removed': len(to_remove),
        'clusters': len(clusters),
        'threshold': threshold,
    }

    logger.info(f"✅ Déduplication: {stats['total_before']} → {stats['total_after']} ({stats['removed']} retirés)")
    return texts_unique, indices_kept, stats


def get_duplicate_examples(
    texts: List[str],
    threshold: float = 0.90,
    n: int = 10
) -> List[Dict]:
    """
    Retourne des exemples de doublons détectés pour preview.

    Args:
        texts: Liste de textes
        threshold: Seuil de similarité
        n: Nombre d'exemples max

    Returns:
        Liste de {text1, text2, score}
    """
    duplicates = find_duplicates(texts, threshold)

    # Trier par score décroissant
    duplicates_sorted = sorted(duplicates, key=lambda x: x[2], reverse=True)

    examples = []
    for idx1, idx2, score in duplicates_sorted[:n]:
        examples.append({
            'index1': idx1,
            'index2': idx2,
            'text1': texts[idx1],
            'text2': texts[idx2],
            'similarity': round(score, 3),
        })

    return examples


def create_dedup_groups(
    clusters: List[Set[int]]
) -> Dict[int, uuid.UUID]:
    """
    Crée des group_id pour chaque cluster de doublons.

    Args:
        clusters: Clusters de doublons

    Returns:
        Mapping {index: group_id}
    """
    mapping = {}

    for cluster in clusters:
        group_id = uuid.uuid4()
        for idx in cluster:
            mapping[idx] = group_id

    return mapping


# ==============================================
# Version optimisée pour gros volumes (TODO: MVP+)
# ==============================================

def deduplicate_texts_optimized(
    texts: List[str],
    threshold: float = 0.90,
    use_minhash: bool = False
) -> Tuple[List[str], List[int], Dict]:
    """
    Version optimisée avec MinHash LSH pour gros volumes.
    TODO: Implémenter pour MVP+ si besoin.

    Pour le MVP, utiliser deduplicate_texts() qui est O(n²) mais simple.
    """
    # Pour l'instant, déléguer à la version standard
    logger.warning("Version optimisée non implémentée, utilisation de la version standard")
    return deduplicate_texts(texts, threshold)
