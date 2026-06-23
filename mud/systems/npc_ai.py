import asyncio
import json
import logging
from typing import TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from entities.npc import NPC
    from entities.player import Player

log = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3"
CONTEXT_WINDOW = 10  # last N messages kept per NPC


async def get_npc_response(npc: "NPC", player: "Player", message: str) -> str:
    user_msg = {"role": "user", "content": f'{player.name} says: "{message}"'}
    npc.conversation_history.append(user_msg)

    # Keep context bounded
    history = npc.conversation_history[-(CONTEXT_WINDOW * 2):]

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": npc.system_prompt},
            *history,
        ],
        "stream": False,
        "options": {
            "temperature": 0.8,
            "num_predict": 200,
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OLLAMA_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    log.error(f"Ollama error {resp.status}: {body}")
                    return _fallback(npc)
                data = await resp.json()
                response_text = data["message"]["content"].strip()
    except asyncio.TimeoutError:
        log.warning(f"Ollama timeout for NPC {npc.name}")
        return _fallback(npc)
    except aiohttp.ClientConnectorError:
        log.warning("Ollama not reachable — using fallback dialogue")
        return _fallback(npc)
    except Exception as e:
        log.exception(f"NPC AI error: {e}")
        return _fallback(npc)

    npc.conversation_history.append({"role": "assistant", "content": response_text})
    return response_text


def _fallback(npc: "NPC") -> str:
    fallbacks = {
        "durnan":         "*grunts and polishes a tankard* One gold to use the well. Don't die down there.",
        "halaster":       "Ah, visitors! How... unexpected. And yet not. Nothing in Undermountain surprises me anymore.",
        "jhelnae":        "State your business quickly. I have little patience for surface-dwellers.",
        "irae":           "*ignores you entirely, muttering incantations*",
    }
    name_key = npc.name.lower().split()[0]
    return fallbacks.get(name_key, f"{npc.name} regards you with an unreadable expression.")
