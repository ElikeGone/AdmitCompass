"""Small LIVE check of the Ask AI copilot against a running local server (makes real, paid gpt-6-luna calls).

    .venv\\Scripts\\python scripts\\copilot_live_check.py [http://127.0.0.1:8000]

Asks 3 fixed questions (at most 2 model calls each) and writes experiments/copilot/live_check.md with answers, citations,
grounding outcome, token usage and latency. No API key is read or printed by this script.
"""
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parents[1] / "experiments" / "copilot" / "live_check.md"
QUESTIONS = [("Why is MIT Sloan recommended for this profile?", {"run": "demo"}),
             ("Compare Yale and Booth for my career goal.", {"run": "demo"}),
             ("Will McKinsey sponsor me?", {"run": "demo"})]

conv = f"live-check-{uuid.uuid4().hex[:10]}"
lines = ["# Ask AI — live check (real gpt-6-luna calls)", "", f"Server: {BASE} · conversation `{conv}` · {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", ""]
ok_all, hist = True, []
for q, ctx in QUESTIONS:
    t = time.time()
    r = httpx.post(f"{BASE}/api/copilot/chat", headers={"Origin": BASE}, timeout=150,
                   json={"conversation_id": conv, "message": q, "history": hist, "context": ctx})
    dt = round(time.time() - t, 1)
    lines += [f"## {q}", ""]
    if r.status_code != 200:
        ok_all = False
        lines += [f"**HTTP {r.status_code}:** {r.text[:300]}", ""]
        continue
    j = r.json()
    u, g = j["usage"], j["grounding"]
    ok = j["mode"] == "live" and u["model_calls"] >= 1 and j["answer"].strip() != ""
    ok_all &= ok
    lines += [f"_type: {j['answer_type']} · model calls {u['model_calls']} · input {u.get('input_tokens')} / output {u.get('output_tokens')} "
              f"(reasoning {u.get('reasoning_tokens')}) tokens · {dt} s · grounding: repaired={g['repaired']} fallback={g['fallback']}_", "",
              j["answer"], ""]
    lines += [f"- [{c['n']}] {c['source_title']} — {c['source_url']}" for c in j["citations"]]
    if j["uncertainties"]:
        lines.append("- Uncertain: " + "; ".join(j["uncertainties"]))
    if j.get("budget"):
        lines.append(f"- Conversation budget used: {json.dumps(j['budget'])}")
    lines.append("")
    hist += [{"role": "user", "content": q}, {"role": "assistant", "content": j["answer"]}]
lines.insert(3, f"**Result: {'WORKS' if ok_all else 'PROBLEMS'}**")
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
sys.exit(0 if ok_all else 1)
