"""
LLM Client abstraction supporting Google Gemini API and local Ollama with performance optimizations.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def call_ollama(prompt: str, system_instruction: str = None) -> str:
    primary_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3:latest")
    
    # Candidate URLs to try in order
    candidate_urls = [primary_url]
    for alt in ["http://127.0.0.1:11434", "http://localhost:11434", "http://host.docker.internal:11434"]:
        if alt not in candidate_urls:
            candidate_urls.append(alt)
    
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    last_err = None
    for url in candidate_urls:
        try:
            res = requests.post(
                f"{url}/api/chat",
                json={
                    "model": ollama_model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 512
                    }
                },
                timeout=5
            )
            if res.status_code == 200:
                msg = res.json().get("message", {})
                return msg.get("content", "").strip()
            last_err = f"HTTP {res.status_code}: {res.text}"
        except Exception as e:
            last_err = str(e)
            continue
            
    raise RuntimeError(f"Failed to call local Ollama model (tried {candidate_urls}): {last_err}")

def call_llm(prompt: str, system_instruction: str = None) -> str:
    provider = os.getenv("LLM_PROVIDER", "").lower().strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    
    # If explicitly set to 'ollama' or if Gemini key is invalid/not provided, use Ollama directly
    if provider == "ollama" or not (gemini_key and gemini_key.startswith("AIza")):
        try:
            return call_ollama(prompt, system_instruction)
        except Exception as e:
            print(f"[LLM Client] Ollama call failed: {e}")
            return "SELECT * FROM data_table LIMIT 10;"
    
    # Otherwise try Gemini API first
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=gemini_key,
            temperature=0.1
        )
        messages = []
        if system_instruction:
            messages.append(("system", system_instruction))
        messages.append(("user", prompt))
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as inner_e:
            print(f"[LLM Client] Gemini failed: {e} | Falling back to local Ollama...")
            try:
                return call_ollama(prompt, system_instruction)
            except Exception as final_e:
                print(f"[LLM Client] Ollama fallback failed: {final_e}")
                return "SELECT * FROM data_table LIMIT 10;"



