#!/usr/bin/env python3
"""
AI Cortex Live Internet Search Client
Sends grounded queries to the AI server on 192.168.0.235:8000
"""
import sys
import json
import urllib.request
import urllib.error

SERVER_URL = "http://192.168.0.235:8000/v1/chat/completions"

def ask_ai(prompt: str):
    print(f"\n🔍 Querying AI Cortex (AGY Real-Time Search)...")
    payload = {
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "require_verification": True
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SERVER_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            res = json.loads(response.read().decode("utf-8"))
            answer = res["choices"][0]["message"]["content"]
            model = res.get("model", "unknown")
            print(f"\n[{model}] Answer:\n")
            print(answer)
            print()
    except urllib.error.HTTPError as e:
        print(f"\n❌ Server error ({e.code}): {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        ask_ai(query)
    else:
        print("=== AI Cortex Real-Time Internet Search ===")
        print("Type your query or 'exit' to quit.\n")
        while True:
            try:
                user_input = input("You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ["exit", "quit", "q"]:
                    break
                ask_ai(user_input)
            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break
