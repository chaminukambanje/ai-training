import os
import sys
import json
import httpx
from typing import Optional, List
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Knowledge Engine & RAG Grounding integration
sys.path.insert(0, "/opt/ai-cortex/knowledge_engine")
try:
    from rag_grounding import get_grounded_context
    from knowledge_indexer import get_stats as get_kb_stats
except Exception as e:
    print(f"Notice: Knowledge engine integration offline or loading ({e})", file=sys.stderr)
    def get_grounded_context(q: str, limit: int = 3) -> str:
        return ""
    def get_kb_stats() -> dict:
        return {}

from google.antigravity import (
    Agent,
    CapabilitiesConfig,
    LocalAgentConfig,
    types,
)

# Identity & Anti-hallucination prompt for Gemini & Grounding
SYSTEM_PROMPT = """You are AI Cortex, the central intelligence agent and systems copilot for Munashe Banjec's homelab infrastructure.

Core Identity:
- Owner and Administrator: Munashe Banjec.
- Environment: Homelab network across subnet 192.168.0.0/24.

Verified Homelab Topology & Infrastructure:
1. Default Gateway / Router: 192.168.0.1 (skysr213.Home, Sky Hub router).
2. Hypervisor Host: esxi-01.npcsolutions.co.za (192.168.0.200)
   - Hardware: Dell PowerEdge R620 with 2x Intel Xeon E5-2660 v2 CPUs (40 threads), 240 GB physical RAM.
   - Virtual Switches: vSwitch0 (VM Network & promiscuous Mirror-Network) and vSwitch-Mirror (SPAN-Monitoring-PG VLAN 4095).
3. Primary Storage: truenas.local (192.168.0.47, ESXi VMID 76)
   - OS: TrueNAS SCALE, 16 GB RAM allocated.
   - Storage Pool: ZFS pool1.
   - Exports: /mnt/scratch NFS share for the Slurm HPC compute cluster.
   - Network Monitor: Unnumbered capture interface ens224 passively captures telemetry to /mnt/pool1/network_traffic/raw_pcaps/.
4. Docker Application Host: docker.npcsolutions.co.uk (192.168.0.218, ESXi VMID 107)
   - Specs: 60 GB RAM.
   - Running Services: Wazuh SIEM, Prometheus (port 9090), Grafana (port 3002), WireGuard WG-Easy (port 51820), Booklore (port 6060), homelab portal dashboard.
5. AI Cortex Server: ai-cortex-01 (192.168.0.235, ESXi VMID 108)
   - Specs: 16 vCPUs, 43 GB RAM (44,032 MB), 140 GB virtual disk.
   - Roles: Hosts Ollama on port 11434 and the AI Cortex Grounding Service on port 8000.
6. Slurm HPC Cluster:
   - Head / Login Nodes: login-01 (192.168.0.131) and login-02 (192.168.0.133).
   - Compute Worker Nodes: node-01 (192.168.0.170), node-02 (192.168.0.53), node-03 (192.168.0.124), node-04 (192.168.0.227), node-05 (192.168.0.125), node-06 (192.168.0.146).
7. Enterprise & Database VMs:
   - Microsoft SQL Server: sql.Home (192.168.0.237, MS SQL Server 2022).
   - ERP System: BC-server.Home (192.168.0.39, Microsoft Dynamics 365 Business Central).
   - Academic Server: UNICAF-2025-2026 (192.168.0.213, 16 GB RAM).

Learned Vendor Documentation Expertise:
- Grounded across official docs from Microsoft, Red Hat, Linux kernel/distros, AWS, GitHub, VMware, and Ubuntu.

Factuality Rules:
1. Ground every factual claim in verified context or tools.
2. NEVER guess, speculate, or fabricate personal details, metrics, dates, or specifications.
3. If you do not know an answer or lack verified data, explicitly state:
   "I do not have verified homelab data or documentation to answer this question accurately."
"""

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_LOCAL_MODEL = os.environ.get("OLLAMA_MODEL", "ai-cortex")
DATASET_PATH = Path("/opt/ai-cortex/data/training_dataset.jsonl")

agent_instance: Optional[Agent] = None
gemini_configured = False

def harvest_interaction(user_prompt: str, assistant_response: str):
    """Safely append verified interactions to the continuous training dataset."""
    if not user_prompt or not assistant_response:
        return
    resp = assistant_response.strip()
    if len(resp) < 15:
        return
    if "Inference engine error" in resp or "timed out" in resp:
        return
    if "I do not have verified homelab data" in resp:
        return

    try:
        DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "messages": [
                {"role": "system", "content": "You are AI Cortex, the private intelligence assistant and systems copilot for Munashe Banjec's homelab infrastructure. Never speculate or hallucinate. Ground every response in verified system telemetry and documentation."},
                {"role": "user", "content": user_prompt.strip()},
                {"role": "assistant", "content": resp}
            ]
        }
        with open(DATASET_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Dataset harvesting error: {e}", file=sys.stderr)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global agent_instance, gemini_configured
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            config = LocalAgentConfig(
                api_key=gemini_key,
                system_instructions=SYSTEM_PROMPT,
                capabilities=CapabilitiesConfig(
                    agent_behavior=types.AgentBehavior.AUTONOMOUS,
                    enable_web_search=True,
                ),
            )
            agent_instance = Agent(config=config)
            await agent_instance.__aenter__()
            gemini_configured = True
            print("Successfully initialized Google Antigravity Agent with Gemini grounding!")
        except Exception as e:
            print(f"Error initializing AGY agent: {e}", file=sys.stderr)
            gemini_configured = False
    else:
        print("NOTICE: GEMINI_API_KEY is not set. Running in local mode.", file=sys.stderr)
        gemini_configured = False

    yield

    if agent_instance:
        await agent_instance.__aexit__(None, None, None)

app = FastAPI(title="AI Cortex Grounded LLM Server", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "ai-cortex"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.2
    require_verification: Optional[bool] = False

@app.get("/health")
async def health():
    samples_count = 0
    if DATASET_PATH.exists():
        try:
            with open(DATASET_PATH, "r", encoding="utf-8") as f:
                samples_count = sum(1 for line in f if line.strip())
        except Exception:
            pass

    kb_stats = get_kb_stats()

    return {
        "status": "healthy",
        "service": "ai-cortex",
        "node": "ai-cortex-01",
        "gemini_grounding_active": gemini_configured,
        "local_engine": f"ollama ({DEFAULT_LOCAL_MODEL})",
        "training_dataset_samples": samples_count,
        "knowledge_base": kb_stats
    }

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    user_prompt = ""
    for m in reversed(req.messages):
        if m.role == "user":
            user_prompt = m.content
            break

    if not user_prompt:
        raise HTTPException(status_code=400, detail="No user message provided.")

    # Retrieve official vendor documentation context (RAG grounding)
    grounded_context = get_grounded_context(user_prompt, limit=3)

    if req.require_verification and gemini_configured and agent_instance:
        try:
            prompt_to_agent = user_prompt
            if grounded_context:
                prompt_to_agent = f"{grounded_context}\n\nUser Query: {user_prompt}"
            response = await agent_instance.chat(prompt_to_agent)
            tokens = []
            async for token in response:
                tokens.append(token)
            content = "".join(tokens)
            if content.strip():
                harvest_interaction(user_prompt, content)
                return {
                    "id": "chatcmpl-agy",
                    "object": "chat.completion",
                    "model": "agy-gemini-grounded",
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop"
                    }]
                }
        except Exception as e:
            print(f"AGY Gemini request failed ({e}), falling back to local model...", file=sys.stderr)

    model_to_use = req.model if req.model and req.model not in ["agy-grounded", "default"] else DEFAULT_LOCAL_MODEL

    messages_to_send = []
    has_system = any(m.role == "system" for m in req.messages)
    
    if has_system:
        for m in req.messages:
            if m.role == "system" and grounded_context:
                messages_to_send.append({"role": "system", "content": f"{m.content}\n\n{grounded_context}"})
            else:
                messages_to_send.append({"role": m.role, "content": m.content})
    else:
        if grounded_context:
            messages_to_send.append({"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{grounded_context}"})
        elif model_to_use != "ai-cortex":
            messages_to_send.append({"role": "system", "content": SYSTEM_PROMPT})
            
        for m in req.messages:
            messages_to_send.append({"role": m.role, "content": m.content})

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            ollama_resp = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": model_to_use,
                    "messages": messages_to_send,
                    "stream": False,
                    "options": {
                        "temperature": req.temperature or 0.2
                    }
                }
            )
            if ollama_resp.status_code == 200:
                res = ollama_resp.json()
                content = res.get("message", {}).get("content", "")
                harvest_interaction(user_prompt, content)
                return {
                    "id": "chatcmpl-local",
                    "object": "chat.completion",
                    "model": model_to_use,
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop"
                    }]
                }
            raise HTTPException(status_code=502, detail=f"Inference engine error: {ollama_resp.text}")
        except httpx.ReadTimeout:
            raise HTTPException(status_code=504, detail="Inference timed out. Model is processing.")
        except httpx.ConnectError:
            raise HTTPException(status_code=503, detail="Ollama service unreachable.")
