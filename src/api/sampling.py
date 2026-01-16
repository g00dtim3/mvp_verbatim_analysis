"""
Module de sampling stratifié pour le mode rapide.
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional
from loguru import logger

from src.utils.config import settings


def stratified_sample(
    df: pd.DataFrame,
    n_samples: int = None,
    strata_columns: List[str] = None,
    min_per_stratum: int = None,
    cap_per_stratum: int = None,
    seed: int = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    Effectue un échantillonnage stratifié.

    Args:
        df: DataFrame contenant les verbatims
        n_samples: Nombre total d'échantillons souhaités
        strata_columns: Colonnes pour la stratification (par ordre de priorité)
        min_per_stratum: Minimum par strate
        cap_per_stratum: Maximum par strate
        seed: Seed pour reproductibilité

    Returns:
        (df_sampled, stratification_info)
    """
    # Valeurs par défaut
    n_samples = n_samples or settings.sample_size_rapid
    min_per_stratum = min_per_stratum or settings.min_per_stratum
    cap_per_stratum = cap_per_stratum or settings.cap_per_stratum
    seed = seed or settings.sampling_seed

    # Si le dataset est déjà plus petit que n_samples, tout prendre
    if len(df) <= n_samples:
        logger.info(f"Dataset ({len(df)}) <= n_samples ({n_samples}), pas de sampling")
        return df, {
            'strategy': 'no_sampling',
            'total_available': len(df),
            'total_sampled': len(df),
        }

    # Déterminer les colonnes de stratification
    if strata_columns is None:
        strata_columns = _detect_strata_columns(df)

    if not strata_columns:
        # Pas de strates, sampling aléatoire simple
        logger.info("Pas de colonnes de stratification, sampling aléatoire simple")
        sampled = df.sample(n=n_samples, random_state=seed)
        return sampled, {
            'strategy': 'random',
            'total_available': len(df),
            'total_sampled': n_samples,
        }

    # Stratification
    logger.info(f"Stratification sur: {strata_columns}")

    # Créer une colonne de strate combinée
    df = df.copy()
    df['_stratum'] = df[strata_columns].fillna('unknown').astype(str).agg('|'.join, axis=1)

    # Compter par strate
    strata_counts = df['_stratum'].value_counts()

    logger.debug(f"Nombre de strates: {len(strata_counts)}")

    # Calculer les quotas par strate
    strata_quotas = _calculate_strata_quotas(
        strata_counts,
        n_samples,
        min_per_stratum,
        cap_per_stratum
    )

    # Échantillonner par strate
    sampled_dfs = []
    strata_info = {}

    for stratum, quota in strata_quotas.items():
        stratum_df = df[df['_stratum'] == stratum]
        available = len(stratum_df)

        # Prendre min(quota, available)
        n_take = min(quota, available)

        if n_take > 0:
            sampled_stratum = stratum_df.sample(n=n_take, random_state=seed)
            sampled_dfs.append(sampled_stratum)

            strata_info[stratum] = {
                'available': available,
                'sampled': n_take,
                'quota': quota,
            }

    # Combiner
    df_sampled = pd.concat(sampled_dfs, ignore_index=True)

    # Retirer la colonne temporaire
    df_sampled = df_sampled.drop(columns=['_stratum'])

    logger.info(f"✅ Sampling stratifié: {len(df)} → {len(df_sampled)} verbatims")

    return df_sampled, {
        'strategy': 'stratified',
        'strata_columns': strata_columns,
        'total_available': len(df),
        'total_sampled': len(df_sampled),
        'n_strata': len(strata_info),
        'strata_details': strata_info,
    }


def _detect_strata_columns(df: pd.DataFrame) -> List[str]:
    """
    Détecte automatiquement les colonnes pertinentes pour la stratification.

    Ordre de priorité:
    1. sentiment
    2. language
    3. page_type / category

    Args:
        df: DataFrame

    Returns:
        Liste de colonnes (par ordre de priorité)
    """
    priority_columns = [
        'sentiment',
        'language',
        'page_type',
        'category',
    ]

    available = [col for col in priority_columns if col in df.columns]

    logger.debug(f"Colonnes de stratification détectées: {available}")
    return available


def _calculate_strata_quotas(
    strata_counts: pd.Series,
    total_samples: int,
    min_per_stratum: int,
    cap_per_stratum: int
) -> Dict[str, int]:
    """
    Calcule les quotas par strate.

    Stratégie:
    1. Allouer le minimum à chaque strate
    2. Distribuer le reste proportionnellement
    3. Appliquer le cap

    Args:
        strata_counts: Nombre de verbatims par strate
        total_samples: Nombre total d'échantillons
        min_per_stratum: Minimum par strate
        cap_per_stratum: Maximum par strate

    Returns:
        Dictionnaire {stratum: quota}
    """
    n_strata = len(strata_counts)
    quotas = {}

    # 1. Allouer le minimum
    remaining = total_samples - (n_strata * min_per_stratum)

    if remaining < 0:
        # Pas assez pour donner le min à tous, distribution égale
        logger.warning(f"Pas assez d'échantillons pour le min par strate, distribution égale")
        quota_per_stratum = total_samples // n_strata
        for stratum in strata_counts.index:
            quotas[stratum] = quota_per_stratum
        return quotas

    # 2. Distribuer le reste proportionnellement
    total_count = strata_counts.sum()

    for stratum, count in strata_counts.items():
        # Allocation de base
        base_quota = min_per_stratum

        # Allocation proportionnelle du reste
        proportion = count / total_count
        proportional_quota = int(remaining * proportion)

        # Total
        quota = base_quota + proportional_quota

        # Appliquer le cap
        quota = min(quota, cap_per_stratum)

        quotas[stratum] = quota

    # 3. Ajustement final pour atteindre exactement total_samples
    current_total = sum(quotas.values())

    if current_total < total_samples:
        # Distribuer le surplus aux strates les plus grandes (sous le cap)
        diff = total_samples - current_total
        for stratum in sorted(strata_counts.index, key=lambda x: strata_counts[x], reverse=True):
            if diff <= 0:
                break
            if quotas[stratum] < cap_per_stratum:
                quotas[stratum] += 1
                diff -= 1

    return quotas


def format_stratification_summary(strata_info: Dict) -> str:
    """
    Formate un résumé de la stratification pour affichage UI.

    Args:
        strata_info: Info retournée par stratified_sample

    Returns:
        Texte formaté
    """
    if strata_info.get('strategy') == 'random':
        return f"Stratification : Échantillonnage aléatoire simple ({strata_info['total_sampled']} verbatims)"

    if strata_info.get('strategy') == 'no_sampling':
        return f"Stratification : Aucune (dataset complet : {strata_info['total_sampled']} verbatims)"

    # Stratifié
    strata_cols = strata_info.get('strata_columns', [])
    n_strata = strata_info.get('n_strata', 0)

    summary = f"Stratification appliquée : {', '.join(strata_cols)} ({n_strata} strates)"
    return summary


def get_sampling_preview(
    df: pd.DataFrame,
    strata_columns: List[str]
) -> pd.DataFrame:
    """
    Génère un aperçu de la distribution par strate (avant sampling).

    Args:
        df: DataFrame
        strata_columns: Colonnes de stratification

    Returns:
        DataFrame avec distribution par strate
    """
    if not strata_columns:
        return pd.DataFrame({'info': ['Pas de stratification']})

    # Créer strate combinée
    df = df.copy()
    df['_stratum'] = df[strata_columns].fillna('unknown').astype(str).agg('|'.join, axis=1)

    # Compter
    distribution = df['_stratum'].value_counts().reset_index()
    distribution.columns = ['Strate', 'Nombre de verbatims']
    distribution['% du dataset'] = (distribution['Nombre de verbatims'] / len(df) * 100).round(1)

    return distribution
