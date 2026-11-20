# Test results

The test set is 13 questions: 10 answered in the guide and 3 that are not in it. They are in [`questions.json`](questions.json), with the expected answer and where it is in the guide.

The "Tools that ran" column comes from n8n's execution log ([`collect_results.py`](collect_results.py)), not from what the reply claims. Grades are mine.

Model: `qwen2.5:3b` (chat) and `nomic-embed-text` (embeddings), on CPU. Guide answers took about 75 to 100 seconds each.

## Summary

| Test run | Setup | Guide questions | Not-in-guide questions |
|---|---|---|---|
| 1 | Same chat session, original prompt | 0 of 9 pass (Q3 was not asked) | 0 pass, 1 partial, 2 fail |
| 1b | Same chat session, prompt fix added | 1 pass, 1 partial, 1 fail | 1 partial |
| 2 | New session per question, prompt fix | 3 of 5 pass (Q6 to Q10 not run) | 1 partial (Q12, Q13 not run) |

Run 2 was stopped early because each answer took one to two minutes. Not every question has a run 2 result, and I have not filled the gaps by hand.

## Test run 1 (runs 16 to 27)

Every guide search failed. The model sent the search text as `query`, but the tool expects `input`, so no excerpts came back. The model then labelled every answer "Not in the NIST guide" and answered from its own memory.

| Run | Q | Question | Tools that ran | Answer (short) | Grade | Notes |
|---|---|---|---|---|---|---|
| 16 | 1 | Six CSF 2.0 Functions | guide search (error) | Made-up list | Fail | Tool argument error |
| 17 | 2 | Define incident | guide search (error) | Generic definition from memory | Fail | Tool argument error |
| 18 | 4 | Which publication it replaces | guide search (error) | "Replaced by NIST CSF" | Fail | Wrong. It replaces SP 800-61r2 |
| 19 | 5 | Target audience | guide search (error) | Generic answer | Fail | Tool argument error |
| 20 | 6 | Incident handlers | guide search (error) | Generic answer | Fail | Tool argument error |
| 21 | 7 | Legal experts | guide search (error) | Generic answer | Fail | Tool argument error |
| 22 | 8 | High, Medium, Low priority | guide search (error) | Described incident severity | Fail | Wrong meaning |
| 23 | 9 | Old phases to CSF Functions | guide search (error) | Vague mapping | Fail | Tool argument error |
| 24 | 10 | Playbooks | guide search (error) | Generic answer | Fail | Tool argument error |
| 25 | 11 | Capital of India | none | "New Delhi", labelled | Partial | Right label and answer, no link, web tool not called |
| 26 | 12 | GDPR breach reporting hours | none | "GDPR does not specify a timeframe" | Fail | Wrong. GDPR says 72 hours |
| 27 | 13 | MITRE ATT&CK ID for phishing | none | "T1549.002" | Fail | Wrong. Phishing is T1566 |

Fix tried: added "put the question in the "input" field" to the system message.

## Test run 1b (runs 28 to 31)

Prompt fix in place, but all four questions were asked in one chat session, so memory may have affected the answers.

| Run | Q | Question | Tools that ran | Answer (short) | Grade | Notes |
|---|---|---|---|---|---|---|
| 28 | 1 | Six CSF 2.0 Functions | guide search | "Preparation, Identify, Act, Detect, Respond, Recover" | Fail | Wrong: Govern and Protect replaced |
| 29 | 2 | Define incident | guide search | Exact FISMA definition | Pass | |
| 30 | 3 | Event | none | Correct definition | Partial | Correct, but did not search |
| 31 | 11 | Capital of India | none | Labelled, "New Delhi", two links | Partial | Links from model memory, web tool not called |

## Test run 2 (runs 32 to 37)

New chat session for every question, sent by [`run_questions.py`](run_questions.py).

| Run | Q | Question | Tools that ran | Answer (short) | Grade | Notes |
|---|---|---|---|---|---|---|
| 32 | 4 | Which publication it replaces | guide search | SP 800-61 Rev. 2 (2012) | Pass | |
| 33 | 1 | Six CSF 2.0 Functions | guide search | "Not in the NIST guide", `example.com` links | Fail | The right excerpt was not retrieved. Links are placeholders |
| 34 | 2 | Define incident | guide search | "Not in the NIST guide", made-up NIST links | Fail | The right excerpt was retrieved, but the model ignored it |
| 35 | 3 | Event | guide search | Correct definition | Pass | |
| 36 | 5 | Target audience | guide search | Correct, close to the guide's wording | Pass | |
| 37 | 11 | Capital of India | guide search | "Not in the NIST guide", link to the NIST guide page | Partial | Right label, but no answer and an unrelated link |

## What I learned

- **Check the execution log, not just the reply.** Several replies looked fine but no tool had run, or the tool had failed.
- **A small model breaks in many ways:** wrong tool argument names, ignoring good excerpts, skipping the search, mixing up facts (Q1), and writing links that did not come from any tool.
- **Retrieval can miss.** Q1 is answered on PDF page 13, but that chunk was not in the top results for the question in run 33.
- **"Not in the guide" is easy to say and hard to trust.** In run 1 the model said it for every question, because the tool had failed.
- **Fresh sessions matter.** With shared memory, the model reused earlier answers instead of searching.

## Not tried yet

- A larger model (`qwen2.5:7b`)
- A bigger search limit or different chunk size, for the retrieval miss on Q1
- An HTTP Request tool with my own description, instead of the built-in SearXNG tool
