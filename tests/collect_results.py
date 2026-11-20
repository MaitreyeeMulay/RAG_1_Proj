"""Collect chat test results from n8n's execution log.

Read-only. Runs one SELECT against n8n's Postgres (inside Docker) and prints a
Markdown table: run id, chat session, question, which tools actually ran, and
the agent's answer. The Grade and Notes columns are left empty to fill by hand.

Usage (from the project folder):
    python tests/collect_results.py --last 13
    python tests/collect_results.py --from-id 32
    python tests/collect_results.py --from-id 32 --out tests/run2_raw.md

It never prints database credentials: psql reads them from the container's
own environment.
"""

import argparse
import json
import subprocess
import sys

TIMEOUT_SECONDS = 15
DEFAULT_CONTAINER = "self-hosted-ai-starter-kit-postgres-1"
WORKFLOW_NAME = "chat"
TRIGGER_NODE = "When chat message received"
AGENT_NODE = "AI Agent"
TOOL_NODES = ("search_nist_guide", "searxng-search")


def build_sql(last, from_id):
    where = f"w.name = '{WORKFLOW_NAME}'"
    if from_id is not None:
        # N runs counting forward from from_id.
        where += f" AND e.id >= {int(from_id)}"
        order = "ASC"
    else:
        # Newest N runs.
        order = "DESC"
    return (
        "SELECT id, data FROM ("
        " SELECT e.id, d.data FROM execution_entity e"
        " JOIN execution_data d ON d.\"executionId\" = e.id"
        " JOIN workflow_entity w ON w.id = e.\"workflowId\""
        f" WHERE {where} ORDER BY e.id {order} LIMIT {int(last)}"
        ") t ORDER BY id;"
    )


def fetch_rows(container, sql):
    cmd = [
        "docker", "exec", container, "sh", "-c",
        'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -F "\t" -c "$0"', sql,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8",
        timeout=TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        sys.exit(f"psql failed: {result.stderr.strip()}")
    rows = []
    for line in result.stdout.splitlines():
        if "\t" in line:
            run_id, data = line.split("\t", 1)
            rows.append((int(run_id), data))
    return rows


def unflatten(text):
    """n8n stores run data in 'flatted' format: one array where string
    values inside objects and lists are indexes into that array."""
    arr = json.loads(text)
    seen = {}

    def revive(index):
        index = int(index)
        if index in seen:
            return seen[index]
        value = arr[index]
        if isinstance(value, list):
            out = []
            seen[index] = out
            out.extend(revive(x) if isinstance(x, str) else x for x in value)
        elif isinstance(value, dict):
            out = {}
            seen[index] = out
            for key, x in value.items():
                out[key] = revive(x) if isinstance(x, str) else x
        else:
            out = value
            seen[index] = out
        return out

    return revive(0)


def first_json(run_data, node):
    try:
        return run_data[node][0]["data"]["main"][0][0]["json"]
    except (KeyError, IndexError, TypeError):
        return {}


def node_error(run_data, node):
    try:
        err = run_data[node][0].get("error")
    except (KeyError, IndexError, TypeError):
        return None
    return err.get("message") if isinstance(err, dict) else None


def summarize(run_id, data):
    run_data = unflatten(data).get("resultData", {}).get("runData", {})
    trigger = first_json(run_data, TRIGGER_NODE)
    answer = first_json(run_data, AGENT_NODE).get("output")

    tools = []
    for tool in TOOL_NODES:
        if tool in run_data:
            err = node_error(run_data, tool)
            tools.append(f"{tool} (error: {err})" if err else tool)

    if answer is None:
        answer = f"(no answer; agent error: {node_error(run_data, AGENT_NODE)})"

    return {
        "run": run_id,
        "session": (trigger.get("sessionId") or "")[:8],
        "question": (trigger.get("chatInput") or "").strip(),
        "tools": ", ".join(tools) or "none",
        "answer": answer.strip(),
    }


def cell(text):
    return text.replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def to_markdown(results):
    lines = [
        "| Run | Session | Question | Tools that ran | Answer | Grade | Notes |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['run']} | {r['session']} | {cell(r['question'])} | "
            f"{cell(r['tools'])} | {cell(r['answer'])} |  |  |"
        )
    sessions = [r["session"] for r in results]
    if len(set(sessions)) < len(sessions):
        lines.append("")
        lines.append("Warning: some runs share a chat session, so memory may affect answers.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--last", type=int, default=13, help="how many runs (default 13)")
    parser.add_argument("--from-id", type=int, help="only runs with id >= this")
    parser.add_argument("--container", default=DEFAULT_CONTAINER)
    parser.add_argument("--out", help="also write the table to this file")
    args = parser.parse_args()

    rows = fetch_rows(args.container, build_sql(args.last, args.from_id))
    if not rows:
        sys.exit("No chat runs found.")
    table = to_markdown([summarize(run_id, data) for run_id, data in rows])

    print(table)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(table + "\n")


if __name__ == "__main__":
    main()
