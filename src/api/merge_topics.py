"""
Module de fusion des thèmes (2 passes: algorithmique + LLM).
"""

from typing import List, Dict, Set, Tuple
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict
import uuid
from loguru import logger

from src.llm.client import call_llm_json
from src.llm.prompts import build_merge_messages
from src.utils.config import settings


class TopicMerger:
    """Gestionnaire de fusion de thèmes."""

    def __init__(
        self,
        fuzzy_threshold: float = None,
        jaccard_threshold: float = None
    ):
        """
        Initialise le merger.

        Args:
            fuzzy_threshold: Seuil fuzzy pour Pass 1
            jaccard_threshold: Seuil Jaccard pour Pass 1
        """
        self.fuzzy_threshold = fuzzy_threshold or settings.fuzzy_merge_threshold
        self.jaccard_threshold = jaccard_threshold or settings.jaccard_merge_threshold

        logger.info(
            f"TopicMerger initialisé: fuzzy={self.fuzzy_threshold}, "
            f"jaccard={self.jaccard_threshold}"
        )

    def merge_two_pass(
        self,
        topics: List[Dict]
    ) -> Tuple[List[Dict], Dict]:
        """
        Fusionne les thèmes en 2 passes.

        Args:
            topics: Liste de thèmes bruts
                Chaque thème: {topic_label, subtopic_label, ...}

        Returns:
            (merged_topics, merge_info)
        """
        logger.info(f"Fusion 2-passes de {len(topics)} thèmes...")

        # Pass 1: Fusion algorithmique
        pass1_groups, pass1_info = self._pass1_algorithmic(topics)

        logger.info(f"Pass 1: {len(topics)} thèmes → {len(pass1_groups)} groupes")

        # Pass 2: Fusion sémantique LLM
        merged_topics, pass2_info = self._pass2_llm(pass1_groups, topics)

        logger.info(f"Pass 2: {len(pass1_groups)} groupes → {len(merged_topics)} thèmes finaux")

        merge_info = {
            'total_input': len(topics),
            'total_output': len(merged_topics),
            'pass1': pass1_info,
            'pass2': pass2_info,
        }

        return merged_topics, merge_info

    def _pass1_algorithmic(
        self,
        topics: List[Dict]
    ) -> Tuple[List[Set[int]], Dict]:
        """
        Pass 1: Fusion algorithmique (fuzzy + Jaccard + TF-IDF).

        Args:
            topics: Liste de thèmes

        Returns:
            (groups, info)
            groups: Liste de sets d'indices fusionnés
        """
        n = len(topics)

        # 1. Normaliser les labels
        normalized_keys = []
        for t in topics:
            topic_label = t.get('topic_label', '')
            subtopic_label = t.get('subtopic_label', '')
            key = self._normalize_label(topic_label, subtopic_label)
            normalized_keys.append(key)

        # 2. Calculer les pivot words (TF-IDF)
        pivot_words = self._extract_pivot_words(normalized_keys)

        # 3. Trouver les paires similaires
        similar_pairs = []

        for i in range(n):
            for j in range(i + 1, n):
                # Fuzzy similarity
                fuzzy_score = fuzz.ratio(normalized_keys[i], normalized_keys[j]) / 100.0

                # Jaccard similarity
                jaccard_score = self._jaccard_similarity(
                    normalized_keys[i],
                    normalized_keys[j]
                )

                # Vérifier si même pivot words
                same_pivots = (pivot_words[i] == pivot_words[j]) if pivot_words[i] and pivot_words[j] else False

                # Critères de fusion
                should_merge = (
                    fuzzy_score >= self.fuzzy_threshold
                    or (jaccard_score >= self.jaccard_threshold and same_pivots)
                )

                if should_merge:
                    similar_pairs.append((i, j, fuzzy_score))

        logger.debug(f"Pass 1: {len(similar_pairs)} paires similaires trouvées")

        # 4. Grouper (composantes connexes)
        groups = self._group_indices(similar_pairs, n)

        info = {
            'method': 'algorithmic',
            'pairs_found': len(similar_pairs),
            'groups_created': len(groups),
        }

        return groups, info

    def _pass2_llm(
        self,
        pass1_groups: List[Set[int]],
        topics: List[Dict]
    ) -> Tuple[List[Dict], Dict]:
        """
        Pass 2: Fusion sémantique avec LLM.

        Pour les candidats proches non fusionnés en Pass 1, demander au LLM.

        Args:
            pass1_groups: Groupes de la Pass 1
            topics: Thèmes originaux

        Returns:
            (merged_topics, info)
        """
        # Créer un mapping initial basé sur Pass 1
        topic_to_group = {}
        for group_idx, group in enumerate(pass1_groups):
            for topic_idx in group:
                topic_to_group[topic_idx] = group_idx

        # Identifier les singletons (thèmes non fusionnés)
        singletons = [i for i in range(len(topics)) if i not in topic_to_group]

        # Pour chaque groupe Pass 1, créer un thème fusionné
        merged_topics = []
        llm_calls = 0

        for group_idx, group in enumerate(pass1_groups):
            group_topics = [topics[i] for i in group]

            # Si un seul thème dans le groupe, pas de fusion LLM nécessaire
            if len(group_topics) == 1:
                merged = self._create_merged_topic(
                    group_topics,
                    list(group),
                    merge_method='pass1_single'
                )
                merged_topics.append(merged)
                continue

            # Sinon, demander au LLM de valider/ajuster la fusion
            # (Pour MVP: on fait confiance à Pass 1, LLM optionnel)
            # TODO: Implémenter appel LLM pour validation si nécessaire

            merged = self._create_merged_topic(
                group_topics,
                list(group),
                merge_method='pass1_fuzzy'
            )
            merged_topics.append(merged)

        # Ajouter les singletons
        for idx in singletons:
            merged = self._create_merged_topic(
                [topics[idx]],
                [idx],
                merge_method='no_merge'
            )
            merged_topics.append(merged)

        info = {
            'method': 'llm_semantic',
            'llm_calls': llm_calls,
            'singletons': len(singletons),
        }

        return merged_topics, info

    def _normalize_label(self, topic_label: str, subtopic_label: str = None) -> str:
        """
        Normalise un label de thème.

        Args:
            topic_label: Label du thème
            subtopic_label: Label du sous-thème

        Returns:
            Label normalisé
        """
        # Combiner topic + subtopic
        if subtopic_label:
            combined = f"{topic_label} | {subtopic_label}"
        else:
            combined = topic_label

        # Normaliser
        normalized = combined.lower().strip()

        # Retirer stopwords basiques (optionnel)
        # TODO: Améliorer avec vraie liste de stopwords FR

        return normalized

    def _extract_pivot_words(self, labels: List[str]) -> List[Set[str]]:
        """
        Extrait les mots pivots de chaque label avec TF-IDF.

        Args:
            labels: Liste de labels normalisés

        Returns:
            Liste de sets de mots pivots par label
        """
        if len(labels) < 2:
            return [set() for _ in labels]

        try:
            # TF-IDF
            vectorizer = TfidfVectorizer(
                max_features=5,
                stop_words=None,  # TODO: Ajouter stopwords FR
                token_pattern=r'\b\w+\b'
            )

            tfidf_matrix = vectorizer.fit_transform(labels)
            feature_names = vectorizer.get_feature_names_out()

            pivot_words_list = []
            for i in range(len(labels)):
                # Top mots pour ce label
                row = tfidf_matrix[i].toarray()[0]
                top_indices = row.argsort()[-3:][::-1]  # Top 3
                top_words = {feature_names[idx] for idx in top_indices if row[idx] > 0}
                pivot_words_list.append(top_words)

            return pivot_words_list

        except Exception as e:
            logger.warning(f"Erreur TF-IDF: {e}, retour à méthode simple")
            # Fallback: premiers mots de chaque label
            return [set(label.split()[:2]) for label in labels]

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """
        Calcule la similarité de Jaccard entre deux textes.

        Args:
            text1: Premier texte
            text2: Deuxième texte

        Returns:
            Score de similarité (0-1)
        """
        tokens1 = set(text1.split())
        tokens2 = set(text2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union)

    def _group_indices(self, pairs: List[Tuple[int, int, float]], n_topics: int) -> List[Set[int]]:
        """
        Groupe les indices en composantes connexes.

        Args:
            pairs: Liste de (idx1, idx2, score)
            n_topics: Nombre total de thèmes

        Returns:
            Liste de sets d'indices
        """
        # Graph adjacency
        graph = defaultdict(set)
        for idx1, idx2, _ in pairs:
            graph[idx1].add(idx2)
            graph[idx2].add(idx1)

        # DFS pour trouver composantes connexes
        visited = set()
        groups = []

        def dfs(node, group):
            visited.add(node)
            group.add(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    dfs(neighbor, group)

        all_nodes = set(graph.keys())
        for node in all_nodes:
            if node not in visited:
                group = set()
                dfs(node, group)
                groups.append(group)

        return groups

    def _create_merged_topic(
        self,
        topics: List[Dict],
        source_indices: List[int],
        merge_method: str
    ) -> Dict:
        """
        Crée un thème fusionné à partir d'un groupe.

        Args:
            topics: Liste de thèmes à fusionner
            source_indices: Indices des thèmes sources
            merge_method: Méthode de fusion utilisée

        Returns:
            Thème fusionné
        """
        # Choisir le label canonique (le plus fréquent ou le premier)
        canonical_label = topics[0].get('topic_label', '').strip()
        canonical_subtopic = topics[0].get('subtopic_label')

        # Fallback si topic_label est vide: utiliser pain_points ou benefits
        if not canonical_label:
            pain_points = topics[0].get('pain_points', [])
            benefits = topics[0].get('benefits', [])
            if pain_points:
                canonical_label = pain_points[0][:50]  # Premier pain point (tronqué)
            elif benefits:
                canonical_label = benefits[0][:50]  # Premier bénéfice (tronqué)
            else:
                canonical_label = f"Theme_{source_indices[0]}"  # Dernier fallback
            logger.warning(f"topic_label vide, fallback utilisé: {canonical_label}")

        # Collecter les alias
        aliases = []
        for t in topics[1:]:
            label = t.get('topic_label', '').strip()
            sublabel = t.get('subtopic_label')
            if not label:  # Skip empty labels
                continue
            if sublabel:
                aliases.append(f"{label} > {sublabel}")
            else:
                aliases.append(label)

        # Fusionner les listes (pain points, benefits, examples)
        all_pain_points = []
        all_benefits = []
        all_examples = []

        for t in topics:
            all_pain_points.extend(t.get('pain_points', []))
            all_benefits.extend(t.get('benefits', []))
            all_examples.extend(t.get('example_verbatims', []))

        # Dédupliquer
        all_pain_points = list(set(all_pain_points))
        all_benefits = list(set(all_benefits))
        all_examples = list(set(all_examples))[:10]  # Max 10 exemples

        return {
            'canonical_label': canonical_label,
            'canonical_subtopic': canonical_subtopic,
            'aliases': aliases,
            'source_indices': source_indices,
            'merge_method': merge_method,
            'pain_points': all_pain_points,
            'benefits': all_benefits,
            'usage_context': topics[0].get('usage_context', ''),
            'example_verbatims': all_examples,
        }


def merge_topics_from_chunks(
    chunk_topics: List[Dict],
    fuzzy_threshold: float = None,
    jaccard_threshold: float = None
) -> Tuple[List[Dict], Dict]:
    """
    Point d'entrée principal pour fusionner les thèmes de plusieurs chunks.

    Args:
        chunk_topics: Liste de thèmes extraits des chunks
        fuzzy_threshold: Seuil fuzzy (optionnel)
        jaccard_threshold: Seuil Jaccard (optionnel)

    Returns:
        (merged_topics, merge_info)
    """
    merger = TopicMerger(
        fuzzy_threshold=fuzzy_threshold,
        jaccard_threshold=jaccard_threshold
    )

    merged_topics, merge_info = merger.merge_two_pass(chunk_topics)

    return merged_topics, merge_info
