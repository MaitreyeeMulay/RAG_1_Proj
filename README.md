# NIST Incident Response Q&A Agent

A local, free question-answering agent that answers from one public document: **NIST SP 800-61 Rev. 3**, the incident response guide. I built both workflows by hand in n8n. Everything runs on my own computer, with no paid services and no API keys.

This is a learning project. The known issues and failures are written down below on purpose.

## Why I built it

I work in cloud and application support. I wanted hands-on practice with retrieval-augmented generation (RAG) and AI agents that use tools, on a document that matters in my field.

## How it works

Two n8n workflows:

```
Workflow 1: Ingest (run once)
Manual Trigger -> HTTP Request (download the PDF) -> Qdrant Vector Store (insert)
                                                      |- Embeddings Ollama (nomic-embed-text)
                                                      |- Default Data Loader (PDF, split pages)
                                                           |- Recursive Character Text Splitter (overlap 200)

Workflow 2: Chat
Chat Trigger -> AI Agent
                |- Chat model: Ollama (qwen2.5:3b)
                |- Memory: Simple Memory
                |- Tool: search_nist_guide (Qdrant, same embeddings)
                |- Tool: searxng-search (local SearXNG web search)
```

The agent is told to search the guide first, answer only from the excerpts, and name the section or page. If the guide has no answer, it should say "Not in the NIST guide" and fall back to the web.

| Part | What it does |
|---|---|
| n8n | Workflow and agent builder |
| Ollama | Runs the models locally: `qwen2.5:3b` (chat), `nomic-embed-text` (embeddings) |
| Qdrant | Vector database. The guide is stored as 138 chunks |
| SearXNG | Self-hosted web search, bound to `127.0.0.1` only |
| Postgres | n8n's own database |

## What works

- Questions the guide covers get answers from the guide, with a section or page reference.
- Ingest is a single run and the PDF is downloaded straight from NIST.
- Everything is free and runs locally.

## Known issues

- **`llama3.2` broke tool calls.** It wrote the tool call as plain, broken JSON text (`{"name":"search_nist_guide","parameters{"}`) instead of calling the tool. Switching to `qwen2.5:3b` fixed it.
- **A tool name mismatch made the model fake an answer.** When the system message named a tool that did not exist, the model did not fail. It wrote "From the web:" and reused the guide's own link. Lesson: check tool names exactly, and check the execution log, not just the reply.
- **The web search tool is not called.** `qwen2.5:3b` never calls `searxng-search`. When the guide has no answer, it says "Not in the NIST guide" and gives a working search link for the question. So you get a page of results, not a picked-out answer. The SearXNG tool's built-in description says it is for "current events", which may be part of the reason. A bigger model or an HTTP Request tool with my own description might fix it. Not tried yet.
- **Page numbers are PDF pages.** Qdrant stores the PDF page (for example 13), while the guide prints a different page number (5) on the same page.
- **The web can be out of date.** One of the top web results for "NIST incident response" was the old guide (SP 800-61 **Rev. 2**).
- **Small model, small machine.** Docker had about 8 GB of memory, so I stayed with 3B models.

## Test results

The 10 + 3 question test table (10 questions from the guide, 3 that are not in it) is coming next. Failures will stay in the table.

## Run it yourself

You need Docker Desktop. These steps are for a computer without an Nvidia GPU.

1. Clone the repo and create your `.env`:
   ```
   git clone https://github.com/MaitreyeeMulay/RAG_1_Proj.git
   cd RAG_1_Proj
   cp .env.example .env
   ```
   Replace every placeholder in `.env` with your own long random values.
   Note: the demo credentials from the original starter kit only work with its default encryption key. With your own key you set up the credentials yourself (step 5).

2. Start everything:
   ```
   docker compose --profile cpu up -d
   ```

3. Pull the models:
   ```
   docker exec ollama ollama pull qwen2.5:3b
   docker exec ollama ollama pull nomic-embed-text
   ```

4. Open n8n at http://localhost:5678 and create your owner account.

5. Create three credentials in n8n:
   - Ollama: Base URL `http://ollama:11434`, no API key
   - Qdrant: URL `http://qdrant:6333`, no API key
   - SearXNG: API URL `http://searxng:8080`

   Use the container names, not `localhost`. Inside Docker, `localhost` points at the n8n container itself.

6. Import `Workflows/Ingest.json` and `Workflows/chat.json`, and pick your credentials in each node.

7. Run **Ingest** once. Running it again adds duplicate chunks.

8. Open **chat** and click **Open chat**.

## Credits

- Built on the [n8n self-hosted AI starter kit](https://github.com/n8n-io/self-hosted-ai-starter-kit) (Apache 2.0, see `LICENSE`).
- Source document: [NIST SP 800-61 Rev. 3](https://csrc.nist.gov/pubs/sp/800/61/r3/final), *Incident Response Recommendations and Considerations for Cybersecurity Risk Management*, NIST, April 2025.
