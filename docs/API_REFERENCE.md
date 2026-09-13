# AI Cortex Server API Reference

The AI Cortex Grounded LLM Server runs on port `8000` on `ai-cortex-01` (`192.168.0.235:8000`). It exposes an OpenAI-compatible interface with real-time Retrieval-Augmented Grounding (RAG).

---

## 1. Health & Telemetry Endpoint

### `GET /health`
Returns system health, active inference engines, dataset metrics, and live knowledge base statistics.

#### Request:
```bash
curl -s http://192.168.0.235:8000/health
```

#### Response:
```json
{
    "status": "healthy",
    "service": "ai-cortex",
    "node": "ai-cortex-01",
    "gemini_grounding_active": true,
    "local_engine": "ollama (ai-cortex)",
    "training_dataset_samples": 4951,
    "knowledge_base": {
        "documents": 234,
        "chunks": 4053,
        "domains": {
            "aws": 32,
            "chaminuka_mbanje": 1,
            "github": 26,
            "linux": 27,
            "microsoft": 34,
            "redhat": 10,
            "ubuntu": 43,
            "vmware": 61
        }
    }
}
```

---

## 2. Chat Completions Endpoint

### `POST /v1/chat/completions`
OpenAI-compatible chat completion endpoint with automatic document grounding.

#### Request Headers:
```
Content-Type: application/json
```

#### Request Schema:
```json
{
  "model": "ai-cortex",
  "messages": [
    {
      "role": "user",
      "content": "What are the essential steps to configure a static IP with netplan on Ubuntu?"
    }
  ],
  "temperature": 0.2,
  "require_verification": false
}
```

#### Field Descriptions:
| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `model` | `string` | `"ai-cortex"` | Target model (`ai-cortex`, `qwen2.5:7b`, or `default`). |
| `messages` | `array` | Required | Standard ChatML array of `{role, content}` objects. |
| `temperature` | `float` | `0.2` | Sampling temperature (0.0 to 1.0; 0.2 recommended for factuality). |
| `require_verification` | `boolean` | `false` | When `true`, routes through Google Antigravity Agent with Gemini grounding. |

#### Response Schema:
```json
{
  "id": "chatcmpl-local",
  "object": "chat.completion",
  "model": "ai-cortex",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "To configure a static IP address using netplan on an Ubuntu system..."
      },
      "finish_reason": "stop"
    }
  ]
}
```
