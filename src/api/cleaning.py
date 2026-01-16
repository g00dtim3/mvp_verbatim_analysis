"""
Module de nettoyage des verbatims.
"""

import re
import emoji
from typing import Dict, List
from unidecode import unidecode
from loguru import logger


class TextCleaner:
    """Classe pour nettoyer les verbatims."""

    def __init__(self, options: Dict[str, bool]):
        """
        Initialise le cleaner avec les options.

        Args:
            options: Dictionnaire d'options de nettoyage
                - lowercase: bool
                - remove_urls: bool
                - remove_emojis: bool
                - remove_extra_spaces: bool
                - remove_punctuation: bool
        """
        self.options = options
        logger.debug(f"TextCleaner initialisé avec options: {options}")

    def clean(self, text: str) -> str:
        """
        Nettoie un texte selon les options configurées.

        Args:
            text: Texte à nettoyer

        Returns:
            Texte nettoyé
        """
        if not text or not isinstance(text, str):
            return ""

        cleaned = text

        # 1. Normalisation Unicode
        cleaned = unidecode(cleaned)

        # 2. URLs
        if self.options.get('remove_urls', False):
            cleaned = self._remove_urls(cleaned)

        # 3. Emojis
        if self.options.get('remove_emojis', False):
            cleaned = self._remove_emojis(cleaned)

        # 4. Minuscules
        if self.options.get('lowercase', False):
            cleaned = cleaned.lower()

        # 5. Ponctuation excessive
        if self.options.get('remove_punctuation', False):
            cleaned = self._remove_excessive_punctuation(cleaned)

        # 6. Espaces
        if self.options.get('remove_extra_spaces', False):
            cleaned = self._normalize_spaces(cleaned)

        return cleaned.strip()

    @staticmethod
    def _remove_urls(text: str) -> str:
        """Retire les URLs."""
        # Pattern pour http(s):// et www.
        url_pattern = r'https?://\S+|www\.\S+'
        return re.sub(url_pattern, '', text)

    @staticmethod
    def _remove_emojis(text: str) -> str:
        """Retire les emojis."""
        return emoji.replace_emoji(text, replace='')

    @staticmethod
    def _remove_excessive_punctuation(text: str) -> str:
        """
        Retire la ponctuation excessive.
        Garde 1 occurrence de chaque ponctuation consécutive.
        """
        # Remplacer 2+ ponctuations identiques par 1
        text = re.sub(r'([!?.,;:]){2,}', r'\1', text)
        return text

    @staticmethod
    def _normalize_spaces(text: str) -> str:
        """Normalise les espaces."""
        # Remplacer multiples espaces/tabs/newlines par un seul espace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


def clean_verbatims(
    texts: List[str],
    options: Dict[str, bool]
) -> List[str]:
    """
    Nettoie une liste de verbatims.

    Args:
        texts: Liste de textes
        options: Options de nettoyage

    Returns:
        Liste de textes nettoyés
    """
    cleaner = TextCleaner(options)
    cleaned = [cleaner.clean(t) for t in texts]

    logger.info(f"✅ {len(cleaned)} verbatims nettoyés")
    return cleaned


def get_cleaning_stats(
    original_texts: List[str],
    cleaned_texts: List[str]
) -> Dict:
    """
    Calcule des statistiques sur le nettoyage.

    Args:
        original_texts: Textes originaux
        cleaned_texts: Textes nettoyés

    Returns:
        Dictionnaire de stats
    """
    # Longueur moyenne avant/après
    avg_len_before = sum(len(t) for t in original_texts) / len(original_texts)
    avg_len_after = sum(len(t) for t in cleaned_texts) / len(cleaned_texts)

    # Nombre de textes vides après nettoyage
    empty_after = sum(1 for t in cleaned_texts if len(t.strip()) == 0)

    return {
        'total_verbatims': len(original_texts),
        'avg_length_before': round(avg_len_before, 1),
        'avg_length_after': round(avg_len_after, 1),
        'reduction_pct': round((1 - avg_len_after / avg_len_before) * 100, 1),
        'empty_after_cleaning': empty_after,
    }


def get_default_cleaning_options() -> Dict[str, bool]:
    """
    Retourne les options de nettoyage par défaut.

    Returns:
        Dictionnaire d'options
    """
    return {
        'lowercase': True,
        'remove_urls': True,
        'remove_emojis': True,
        'remove_extra_spaces': True,
        'remove_punctuation': False,  # Garde la ponctuation par défaut
    }


# ==============================================
# Exemples d'usage
# ==============================================

def get_cleaning_examples(
    texts: List[str],
    options: Dict[str, bool],
    n: int = 5
) -> List[Dict[str, str]]:
    """
    Génère des exemples avant/après pour preview.

    Args:
        texts: Textes originaux
        options: Options de nettoyage
        n: Nombre d'exemples

    Returns:
        Liste de {before, after}
    """
    cleaner = TextCleaner(options)
    examples = []

    for i, text in enumerate(texts[:n]):
        cleaned = cleaner.clean(text)
        examples.append({
            'index': i,
            'before': text,
            'after': cleaned,
            'length_before': len(text),
            'length_after': len(cleaned),
        })

    return examples
