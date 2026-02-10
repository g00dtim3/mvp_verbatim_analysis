"""
Pipeline LangGraph pour orchestrer l'analyse complète.
"""

from typing import Dict, List, TypedDict, Optional
from loguru import logger
from langgraph.graph import StateGraph, END
from datetime import datetime

from src.api.analysis_llm import ChunkAnalyzer, create_chunks, extract_all_themes_from_results
from src.api.merge_topics import merge_topics_from_chunks
from src.api.ontology import OntologyGenerator
from src.api.quantification import quantify_topics, get_quantification_summary


class AnalysisState(TypedDict):
    """État du pipeline d'analyse."""
    # Input
    verbatims: List[str]
    brief: str
    mode: str  # 'rapid' ou 'full'

    # Intermediate
    chunks: Optional[List[List[str]]]
    chunk_results: Optional[List[Dict]]
    all_themes: Optional[List[Dict]]
    merged_topics: Optional[List[Dict]]
    topics_with_ontology: Optional[List[Dict]]

    # Output
    topics_quantified: Optional[List[Dict]]

    # Metadata
    status: str
    errors: List[str]
    current_step: str
    stats: Dict


class VerbatimAnalysisPipeline:
    """
    Pipeline d'analyse complète avec LangGraph.

    Workflow:
    1. CreateChunks: Découpage en chunks (si mode full)
    2. AnalyzeChunks: Analyse LLM par chunk
    3. MergeTopics: Fusion des thèmes (2 passes)
    4. GenerateOntology: Génération keywords/regex
    5. Quantify: Comptage Python déterministe
    """

    def __init__(self):
        """Initialise le pipeline."""
        self.graph = self._build_graph()
        logger.info("VerbatimAnalysisPipeline initialisé")

    def _build_graph(self) -> StateGraph:
        """
        Construit le graphe LangGraph.

        Returns:
            StateGraph configuré
        """
        workflow = StateGraph(AnalysisState)

        # Ajouter les nodes
        workflow.add_node("create_chunks", self._create_chunks_node)
        workflow.add_node("analyze_chunks", self._analyze_chunks_node)
        workflow.add_node("merge_topics", self._merge_topics_node)
        workflow.add_node("generate_ontology", self._generate_ontology_node)
        workflow.add_node("quantify", self._quantify_node)

        # Définir les edges
        workflow.set_entry_point("create_chunks")
        workflow.add_edge("create_chunks", "analyze_chunks")
        workflow.add_edge("analyze_chunks", "merge_topics")
        workflow.add_edge("merge_topics", "generate_ontology")
        workflow.add_edge("generate_ontology", "quantify")
        workflow.add_edge("quantify", END)

        return workflow.compile()

    def run(
        self,
        verbatims: List[str],
        brief: str,
        mode: str = 'full'
    ) -> Dict:
        """
        Exécute le pipeline complet.

        Args:
            verbatims: Liste de verbatims (déjà nettoyés)
            brief: Contexte d'analyse
            mode: 'rapid' ou 'full'

        Returns:
            État final avec résultats
        """
        logger.info(f"Démarrage du pipeline: mode={mode}, verbatims={len(verbatims)}")

        # État initial
        initial_state = AnalysisState(
            verbatims=verbatims,
            brief=brief,
            mode=mode,
            chunks=None,
            chunk_results=None,
            all_themes=None,
            merged_topics=None,
            topics_with_ontology=None,
            topics_quantified=None,
            status='pending',
            errors=[],
            current_step='init',
            stats={}
        )

        # Exécuter le graphe
        try:
            final_state = self.graph.invoke(initial_state)
            logger.info("✅ Pipeline terminé avec succès")
            return final_state

        except Exception as e:
            logger.error(f"❌ Erreur pipeline: {e}")
            return {
                **initial_state,
                'status': 'failed',
                'errors': [str(e)]
            }

    def _create_chunks_node(self, state: AnalysisState) -> AnalysisState:
        """Node: Création des chunks."""
        logger.info("Node: CreateChunks")

        verbatims = state['verbatims']
        mode = state['mode']

        try:
            if mode == 'rapid':
                # En mode rapide, les verbatims sont déjà échantillonnés
                # On crée un seul chunk
                chunks = [verbatims]
            else:
                # Mode full: découpage en chunks de 200
                chunks = create_chunks(verbatims)

            state['chunks'] = chunks
            state['current_step'] = 'chunks_created'
            state['stats']['nb_chunks'] = len(chunks)

            logger.info(f"✅ {len(chunks)} chunks créés")
            return state

        except Exception as e:
            logger.error(f"❌ Erreur CreateChunks: {e}")
            state['errors'].append(f"CreateChunks: {str(e)}")
            state['status'] = 'failed'
            return state

    def _analyze_chunks_node(self, state: AnalysisState) -> AnalysisState:
        """Node: Analyse LLM des chunks."""
        logger.info("Node: AnalyzeChunks")

        chunks = state['chunks']
        brief = state['brief']

        try:
            analyzer = ChunkAnalyzer(brief=brief)
            chunk_results = analyzer.analyze_chunks_parallel(chunks)

            # Extraire tous les thèmes
            all_themes = extract_all_themes_from_results(chunk_results)

            state['chunk_results'] = chunk_results
            state['all_themes'] = all_themes
            state['current_step'] = 'chunks_analyzed'
            state['stats']['nb_themes_raw'] = len(all_themes)

            # Compter succès/échecs
            success_count = sum(1 for r in chunk_results if r['status'] == 'success')
            failed_count = len(chunk_results) - success_count

            state['stats']['chunks_success'] = success_count
            state['stats']['chunks_failed'] = failed_count

            if failed_count > 0:
                logger.warning(f"⚠️ {failed_count} chunks ont échoué")
                state['status'] = 'partial'

            logger.info(f"✅ {len(all_themes)} thèmes extraits de {success_count} chunks")
            return state

        except Exception as e:
            logger.error(f"❌ Erreur AnalyzeChunks: {e}")
            state['errors'].append(f"AnalyzeChunks: {str(e)}")
            state['status'] = 'failed'
            return state

    def _merge_topics_node(self, state: AnalysisState) -> AnalysisState:
        """Node: Fusion des thèmes (2 passes)."""
        logger.info("Node: MergeTopics")

        all_themes = state['all_themes']

        try:
            merged_topics, merge_info = merge_topics_from_chunks(all_themes)

            state['merged_topics'] = merged_topics
            state['current_step'] = 'topics_merged'
            state['stats']['nb_topics_merged'] = len(merged_topics)
            state['stats']['merge_info'] = merge_info

            logger.info(f"✅ {len(merged_topics)} thèmes fusionnés")
            return state

        except Exception as e:
            logger.error(f"❌ Erreur MergeTopics: {e}")
            state['errors'].append(f"MergeTopics: {str(e)}")
            state['status'] = 'failed'
            return state

    def _generate_ontology_node(self, state: AnalysisState) -> AnalysisState:
        """Node: Génération de l'ontologie projet."""
        logger.info("Node: GenerateOntology")

        merged_topics = state['merged_topics']

        try:
            generator = OntologyGenerator()
            topics_with_ontology = generator.generate_for_all_topics(merged_topics)

            state['topics_with_ontology'] = topics_with_ontology
            state['current_step'] = 'ontology_generated'

            # Calculer coût total
            total_cost = sum(
                item['ontology'].get('llm_cost', 0)
                for item in topics_with_ontology
            )
            state['stats']['ontology_cost_usd'] = total_cost

            logger.info(f"✅ Ontologie générée pour {len(topics_with_ontology)} thèmes")
            return state

        except Exception as e:
            logger.error(f"❌ Erreur GenerateOntology: {e}")
            state['errors'].append(f"GenerateOntology: {str(e)}")
            state['status'] = 'failed'
            return state

    def _quantify_node(self, state: AnalysisState) -> AnalysisState:
        """Node: Quantification Python."""
        logger.info("Node: Quantify")

        verbatims = state['verbatims']
        topics_with_ontology = state['topics_with_ontology']

        try:
            topics_quantified = quantify_topics(verbatims, topics_with_ontology)

            # Générer résumé
            summary = get_quantification_summary(topics_quantified)

            state['topics_quantified'] = topics_quantified
            state['current_step'] = 'quantified'
            state['stats']['quantification_summary'] = summary

            # Finaliser le statut
            if state.get('status') != 'partial':
                state['status'] = 'success'

            logger.info(f"✅ Quantification terminée: {summary['topics_with_matches']} thèmes avec occurrences")
            return state

        except Exception as e:
            logger.error(f"❌ Erreur Quantify: {e}")
            state['errors'].append(f"Quantify: {str(e)}")
            state['status'] = 'failed'
            return state


# ==============================================
# Helper functions
# ==============================================

def run_full_analysis(
    verbatims: List[str],
    brief: str,
    mode: str = 'full'
) -> Dict:
    """
    Fonction helper pour exécuter l'analyse complète.

    Args:
        verbatims: Liste de verbatims (clean)
        brief: Contexte d'analyse
        mode: 'rapid' ou 'full'

    Returns:
        Résultats de l'analyse
    """
    pipeline = VerbatimAnalysisPipeline()
    return pipeline.run(verbatims, brief, mode)


def get_pipeline_status(state: Dict) -> str:
    """
    Retourne un statut lisible du pipeline.

    Args:
        state: État du pipeline

    Returns:
        Message de statut
    """
    status = state.get('status', 'unknown')
    current_step = state.get('current_step', 'unknown')
    errors = state.get('errors', [])

    if status == 'success':
        return f"✅ Analyse terminée avec succès (étape: {current_step})"
    elif status == 'partial':
        return f"⚠️ Analyse partielle (étape: {current_step})"
    elif status == 'failed':
        error_msg = errors[0] if errors else "Erreur inconnue"
        return f"❌ Analyse échouée (étape: {current_step}): {error_msg}"
    else:
        return f"🔄 En cours (étape: {current_step})"
