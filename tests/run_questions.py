"""Send the test questions to the n8n chat workflow, one new session each.

Needs "Make Chat Publicly Available" switched on in the Chat Trigger while it
runs. Switch it off afterwards.

Each request has a 120-second timeout. Local CPU answers take about 75 seconds,
so the usual 15-second limit is raised for these chat requests only (agreed
with the project owner). Questions run one at a time; a timeout or error is
recorded and the next question still runs.

Usage (from the project folder):
    python tests/run_questions.py                 # all questions
    python tests/run_questions.py --only 1 4 12   # just some

Then build the table from n8n's log:
    python tests/collect_results.py --from-id <first run id>
"""

import argparse
import json
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

CHAT_TIMEOUT_SECONDS = 120
DEFAULT_URL = "http://localhost:5678/webhook/5cb52313-3898-4280-bae9-5de88017b844/chat"
QUESTIONS_FILE = Path(__file__).with_name("questions.json")


def ask(url, question):
    """Hard limit: give up after CHAT_TIMEOUT_SECONDS in total.

    urllib's own timeout only limits each wait for data, not the whole
    request, so the request runs in a daemon thread with a total deadline.
    """
    box = {}

    def worker():
        try:
            box["result"] = _post(url, question)
        except Exception as e:  # passed back to the caller below
            box["error"] = e

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(CHAT_TIMEOUT_SECONDS)
    if t.is_alive():
        raise TimeoutError(f"no answer within {CHAT_TIMEOUT_SECONDS} s")
    if "error" in box:
        raise box["error"]
    return box["result"]


def _post(url, question):
    body = json.dumps({
        "action": "sendMessage",
        "sessionId": uuid.uuid4().hex,  # new session, so no memory carries over
        "chatInput": question,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=CHAT_TIMEOUT_SECONDS) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--only", type=int, nargs="*", help="question ids to run")
    args = parser.parse_args()

    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    if args.only:
        questions = [q for q in questions if q["id"] in args.only]

    for q in questions:
        start = time.monotonic()
        try:
            status, text = ask(args.url, q["question"])
            result = f"HTTP {status}: {text[:150]}"
        except urllib.error.HTTPError as e:
            result = f"HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:150]}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            result = f"FAILED: {e}"
        secs = time.monotonic() - start
        print(f"Q{q['id']:>2} ({secs:5.1f}s) {result}".replace("\n", " "), flush=True)


if __name__ == "__main__":
    main()
