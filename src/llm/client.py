"""
Client OpenAI avec gestion des erreurs et retry.
"""

import openai
from openai import OpenAI
from typing import Optional, List, Dict, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from loguru import logger
import tiktoken

from src.utils.config import settings


# Client OpenAI
client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """Retourne le client OpenAI (singleton)."""
    global client
    if client is None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY non configurée")
        client = OpenAI(api_key=settings.openai_api_key)
    return client


def count_tokens(text: str, model: str = None) -> int:
    """
    Compte le nombre de tokens dans un texte.
    
    Args:
        text: Texte à analyser
        model: Modèle (défaut: settings.openai_model)
        
    Returns:
        Nombre de tokens
    """
    model = model or settings.openai_model
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))


def estimate_cost(input_tokens: int, output_tokens: int, model: str = None) -> float:
    """
    Estime le coût d'un appel LLM.
    
    Prix approximatifs (à mettre à jour):
    - gpt-4-turbo: $0.01/1K input, $0.03/1K output
    - gpt-4: $0.03/1K input, $0.06/1K output
    - gpt-3.5-turbo: $0.0005/1K input, $0.0015/1K output
    """
    model = model or settings.openai_model
    
    # Prix par 1K tokens (input, output)
    pricing = {
        "gpt-4-turbo-preview": (0.01, 0.03),
        "gpt-4-turbo": (0.01, 0.03),
        "gpt-4": (0.03, 0.06),
        "gpt-3.5-turbo": (0.0005, 0.0015),
    }
    
    input_price, output_price = pricing.get(model, (0.01, 0.03))
    
    cost = (input_tokens / 1000 * input_price) + (output_tokens / 1000 * output_price)
    return round(cost, 4)


@retry(
    retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError)),
    stop=stop_after_attempt(settings.llm_max_retries),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=lambda retry_state: logger.warning(
        f"Retry {retry_state.attempt_number}/{settings.llm_max_retries} après erreur"
    )
)
def call_llm(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 4000,
    response_format: Optional[Dict] = None,
    timeout: int = None,
) -> Dict[str, Any]:
    """
    Appelle l'API OpenAI avec retry automatique.
    
    Args:
        messages: Liste de messages [{"role": "...", "content": "..."}]
        model: Modèle à utiliser
        temperature: Température (0-2)
        max_tokens: Tokens max en sortie
        response_format: Format de réponse (ex: {"type": "json_object"})
        timeout: Timeout en secondes
        
    Returns:
        {
            "content": str,  # Réponse
            "tokens_input": int,
            "tokens_output": int,
            "cost": float,
            "model": str,
        }
    """
    model = model or settings.openai_model
    timeout = timeout or settings.llm_timeout
    
    logger.debug(f"Appel LLM: model={model}, messages={len(messages)}")
    
    try:
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = get_client().chat.completions.create(**kwargs)
        
        content = response.choices[0].message.content
        tokens_input = response.usage.prompt_tokens
        tokens_output = response.usage.completion_tokens
        
        result = {
            "content": content,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost": estimate_cost(tokens_input, tokens_output, model),
            "model": model,
        }
        
        logger.debug(f"LLM OK: {tokens_input}+{tokens_output} tokens, ${result['cost']}")
        return result
        
    except openai.BadRequestError as e:
        logger.error(f"BadRequest OpenAI: {e}")
        raise
    except openai.AuthenticationError as e:
        logger.error(f"Erreur auth OpenAI: {e}")
        raise
    except Exception as e:
        logger.error(f"Erreur LLM inattendue: {e}")
        raise


def call_llm_json(
    messages: List[Dict[str, str]],
    **kwargs
) -> Dict[str, Any]:
    """
    Appelle l'API OpenAI avec réponse JSON forcée.
    
    Returns:
        Le résultat de call_llm avec content parsé en JSON
    """
    import json
    
    result = call_llm(
        messages=messages,
        response_format={"type": "json_object"},
        **kwargs
    )
    
    try:
        result["content_json"] = json.loads(result["content"])
    except json.JSONDecodeError as e:
        logger.error(f"Erreur parsing JSON: {e}")
        result["content_json"] = None
        result["json_error"] = str(e)
    
    return result


def test_connection() -> bool:
    """
    Teste la connexion à l'API OpenAI.
    
    Returns:
        True si OK, False sinon
    """
    try:
        result = call_llm(
            messages=[{"role": "user", "content": "Réponds juste 'OK'"}],
            max_tokens=10,
            temperature=0,
        )
        logger.info(f"✅ OpenAI connection OK (model: {result['model']})")
        return True
    except Exception as e:
        logger.error(f"❌ OpenAI connection failed: {e}")
        return False
