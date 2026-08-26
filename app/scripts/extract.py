import json, os, glob

TARGETS = {"brooks-slack-voice", "comment-adversary", "process-scrub-reviewer", "ste100-validator", "scribe"}
root = os.path.expanduser("~/.claude/projects")
files = glob.glob(os.path.join(root, "**", "*.jsonl"), recursive=True)

invocations = {}   # tool_use_id -> record
results = {}       # tool_use_id -> output text


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
        return "\n".join(parts)
    return ""


for path in files:
    try:
        fh = open(path)
    except OSError:
        continue
    with fh:
        for line in fh:
            if '"subagent_type"' not in line and '"tool_use_id"' not in line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            msg = obj.get("message", {})
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use" and c.get("name") in ("Task", "Agent"):
                    inp = c.get("input", {})
                    st = inp.get("subagent_type")
                    if st in TARGETS:
                        invocations[c["id"]] = {
                            "agent_type": st,
                            "timestamp": obj.get("timestamp"),
                            "file": path,
                            "project": path.replace(root + "/", "").split("/")[0],
                            "description": inp.get("description", ""),
                            "prompt": inp.get("prompt", ""),
                        }
                elif c.get("type") == "tool_result":
                    tid = c.get("tool_use_id")
                    if tid:
                        txt = text_of(c.get("content"))
                        if txt:
                            results[tid] = txt

paired = []
for tid, rec in invocations.items():
    rec["output"] = results.get(tid, "")
    rec["has_output"] = tid in results
    rec["tool_use_id"] = tid
    paired.append(rec)

paired.sort(key=lambda r: r.get("timestamp") or "", reverse=True)

by_type = {}
for r in paired:
    by_type.setdefault(r["agent_type"], []).append(r)

with open("/tmp/voice-agent-analysis/raw/all_invocations.json", "w") as f:
    json.dump(paired, f, indent=1)

for t, recs in by_type.items():
    with open(f"/tmp/voice-agent-analysis/raw/{t}.json", "w") as f:
        json.dump(recs, f, indent=1)
    with_out = sum(1 for r in recs if r["has_output"])
    print(f"{t}: {len(recs)} invocations, {with_out} with outputs, newest {recs[0]['timestamp']}, oldest {recs[-1]['timestamp']}")
