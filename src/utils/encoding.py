"""
Utilitaires pour gérer les problèmes d'encodage Unicode.
"""


def fix_double_encoding(text: str) -> str:
    """
    Corrige les problèmes de double encodage UTF-8.

    Exemples:
    - "efficacitÃ©" → "efficacité"
    - "rÃ©sultats" → "résultats"
    - "mÃ©lasma" → "mélasma"

    Args:
        text: Texte avec problème d'encodage

    Returns:
        Texte correctement décodé
    """
    if not isinstance(text, str):
        return text

    try:
        # Si le texte contient des caractères typiques de double encodage UTF-8
        if 'Ã' in text or 'Â' in text:
            # Encoder en latin-1 pour récupérer les bytes originaux
            # puis décoder en UTF-8 correctement
            return text.encode('latin-1').decode('utf-8')
        return text
    except (UnicodeDecodeError, UnicodeEncodeError):
        # Si échec, retourner le texte original
        return text


def fix_encoding_in_list(items: list) -> list:
    """
    Applique la correction d'encodage à tous les éléments d'une liste.

    Args:
        items: Liste de chaînes

    Returns:
        Liste avec chaînes corrigées
    """
    if not items:
        return items

    return [fix_double_encoding(item) if isinstance(item, str) else item for item in items]


def fix_encoding_in_dict(data: dict) -> dict:
    """
    Applique la correction d'encodage récursivement à un dictionnaire.

    Args:
        data: Dictionnaire avec possibles problèmes d'encodage

    Returns:
        Dictionnaire avec encodage corrigé
    """
    if not data:
        return data

    fixed = {}
    for key, value in data.items():
        if isinstance(value, str):
            fixed[key] = fix_double_encoding(value)
        elif isinstance(value, list):
            fixed[key] = fix_encoding_in_list(value)
        elif isinstance(value, dict):
            fixed[key] = fix_encoding_in_dict(value)
        else:
            fixed[key] = value

    return fixed
