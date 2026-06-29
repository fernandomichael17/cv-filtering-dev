"""LLM client initialization and helper utilities.

Uses OpenAI SDK with custom base URL pointing to vLLM server.
All calls use enable_thinking=False via extra_body to prevent
Qwen3 thinking tags in the output.
"""

import json
import logging
import re
import asyncio

from openai import AsyncOpenAI, APIError, APIConnectionError
from app.config import settings

logger = logging.getLogger(__name__)
client = AsyncOpenAI(
    base_url=settings.LLM_API_BASE,
    api_key=settings.LLM_API_KEY,
)

# Lazy-loaded semaphore for global concurrency limit
_llm_semaphore = None

def get_llm_semaphore() -> asyncio.Semaphore:
    """Gets or creates the semaphore attached to the current event loop."""
    global _llm_semaphore
    if _llm_semaphore is None:
        # Gunakan nilai MAX_CONCURRENT_LLM dari env (default 50)
        _llm_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_LLM)
    return _llm_semaphore

def strip_thinking(text: str) -> str:
    """Remove <think>...</think> tags from LLM response (safety fallback)."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def parse_json_response(text: str) -> dict:
    """Extract and parse JSON from LLM response text.

    Handles common LLM quirks: thinking tags, markdown code fences,
    and leading/trailing whitespace.
    """
    text = strip_thinking(text)
    # Remove markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`")
    return json.loads(text)


async def call_llm(
    messages: list[dict],
    max_tokens: int = 512,
    temperature: float = 0.1,
) -> str:
    """Mengirim permintaan chat completion ke server vLLM dengan mekanisme retry dan timeout.

    Menggunakan enable_thinking=False untuk menonaktifkan mode berpikir Qwen3,
    memastikan output JSON bersih tanpa tag <think>.

    Parameter:
        messages (list[dict]): Daftar pesan dengan 'role' dan 'content'.
        max_tokens (int): Jumlah token maksimum yang dihasilkan.
        temperature (float): Suhu sampling (nilai rendah = lebih deterministik).

    Return:
        str: Konten teks mentah dari respons LLM.
    """
    sem = get_llm_semaphore()
    async with sem:
        retries = settings.LLM_MAX_RETRIES
        timeout = settings.LLM_TIMEOUT
        delay = 1.0
        
        for attempt in range(1, retries + 1):
            try:
                # Membungkus dengan asyncio.wait_for untuk membatasi durasi panggilan
                response = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=settings.LLM_MODEL_NAME,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        extra_body={
                            "chat_template_kwargs": {
                                "enable_thinking": False,
                            }
                        },
                    ),
                    timeout=timeout
                )
                
                if response.usage:
                    logger.info(
                        "LLM Token Usage - Prompt: %d | Completion: %d | Total: %d",
                        response.usage.prompt_tokens,
                        response.usage.completion_tokens,
                        response.usage.total_tokens
                    )
                    
                content = response.choices[0].message.content
                logger.debug("LLM response: %s", content[:200])
                return content

            except (asyncio.TimeoutError, TimeoutError, APIError, APIConnectionError) as e:
                logger.warning(
                    "Panggilan LLM gagal (percobaan %d/%d): %s. Mencoba kembali dalam %.1fs...",
                    attempt, retries, str(e), delay
                )
                if attempt == retries:
                    logger.error("Semua %d percobaan panggilan LLM gagal.", retries)
                    raise
                
                await asyncio.sleep(delay)
                delay *= 2.0
