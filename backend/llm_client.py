"""
LLM Client abstraction supporting Google Gemini API and local Ollama with performance optimizations.
"""
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# After an Ollama timeout, 'optional' helper calls (planner, summary, follow-ups...) are
# skipped for a short while so a slow local model doesn't stall every pipeline stage.
_OLLAMA_COOLDOWN_UNTIL = 0.0
OLLAMA_COOLDOWN_SECONDS = 60.0
DEFAULT_OLLAMA_TIMEOUT = 90.0

def call_ollama(prompt: str, system_instruction: str = None, max_tokens: int = None, **kwargs) -> str:
    global _OLLAMA_COOLDOWN_UNTIL
    if kwargs.get("optional") and time.time() < _OLLAMA_COOLDOWN_UNTIL:
        raise RuntimeError("Ollama recently timed out; skipping optional LLM call")
    timeout = kwargs.get("timeout") or DEFAULT_OLLAMA_TIMEOUT
    primary_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3:latest")
    
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    try:
        res = requests.post(
            f"{primary_url}/api/chat",
            json={
                "model": ollama_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": max_tokens or 512,
                    "num_ctx": 4096
                }
            },
            timeout=timeout
        )
        if res.status_code == 200:
            msg = res.json().get("message", {})
            content = msg.get("content", "").strip()
            if content:
                return content
        last_err = f"HTTP {res.status_code}"
    except Exception as e:
        last_err = str(e)
        if isinstance(e, requests.exceptions.Timeout):
            _OLLAMA_COOLDOWN_UNTIL = time.time() + OLLAMA_COOLDOWN_SECONDS
            
    raise RuntimeError(f"Failed to call local Ollama model: {last_err}")

def _call_gemini(prompt: str, system_instruction: str, gemini_key: str) -> str:
    # Prefer newer models first; fall back if unavailable
    model_candidates = ["gemini-3.8-flash", "gemini-3-flash-preview"]
    last_error = None

    for model_name in model_candidates:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024,
                    "topP": 0.95,
                }
            }
            # Deliver system instruction via the dedicated field (much better than user-turn)
            if system_instruction:
                payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

            res = requests.post(url, json=payload, timeout=25.0)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    text = candidates[0]["content"]["parts"][0]["text"].strip()
                    if text:
                        return text
            elif res.status_code in (401, 403):
                # Key invalid or access denied — no point retrying other models
                raise RuntimeError(f"Gemini API auth error ({res.status_code}): {res.text[:200]}")
            elif res.status_code == 429:
                # Quota exceeded on this model, try next
                last_error = f"Quota exceeded on {model_name}"
                continue
            else:
                last_error = f"HTTP {res.status_code} from {model_name}: {res.text[:200]}"
        except RuntimeError:
            raise
        except Exception as e:
            last_error = str(e)
            continue

    raise RuntimeError(f"Gemini API failed after all models: {last_error}")

def call_llm(prompt: str, system_instruction: str = None, max_tokens: int = None, **kwargs) -> str:
    """
    Optional kwargs: timeout (seconds, Ollama), optional=True (fail fast during Ollama cooldown).
    """
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    ollama_kwargs = {k: kwargs[k] for k in ("timeout", "optional") if k in kwargs}
    
    if provider == "gemini" and gemini_key:
        try:
            return _call_gemini(prompt, system_instruction, gemini_key)
        except Exception:
            return call_ollama(prompt, system_instruction, max_tokens=max_tokens, **ollama_kwargs)
            
    if provider == "ollama":
        try:
            return call_ollama(prompt, system_instruction, max_tokens=max_tokens, **ollama_kwargs)
        except Exception as e:
            if gemini_key:
                try:
                    return _call_gemini(prompt, system_instruction, gemini_key)
                except Exception:
                    pass
            raise RuntimeError(f"LLM call failed for Ollama: {e}")

    # Auto mode
    if gemini_key:
        try:
            return _call_gemini(prompt, system_instruction, gemini_key)
        except Exception:
            pass
            
    return call_ollama(prompt, system_instruction, max_tokens=max_tokens, **ollama_kwargs)






