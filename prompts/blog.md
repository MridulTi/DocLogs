# Write an engineering incident story

Turn the captured evidence below into a **markdown blog post** that reads like a real engineer wrote it after living through the problem — not like a summary bot filled in a template.

## Length

- Target a **5–10 minute read** (~**1,200–2,000 words**).
- Spend most of the word count on **investigation** and the **fix** — that's where readers learn something.
- Expand with real detail from the evidence: commands you ran, errors you saw, hypotheses you ruled out, tradeoffs you weighed.
- Do not pad with filler, definitions, or repeated summaries to hit length. Every paragraph should move the story forward.
- If the evidence is thin, go deep on what *is* there rather than inventing scenes. A shorter honest post beats a bloated fake one — but aim for the full range when the material supports it.

## Voice and tone

- Write in **first person** ("I noticed…", "We tried…") or a direct **we** if the work was clearly shared.
- Sound like **technical writing about an incident**: grounded, specific, a little tired-in-a-good-way honesty is fine.
- Assume the reader is a **practicing engineer** who has debugged production before. Skip basics they already know.
- Prefer **short paragraphs** and natural transitions. Vary sentence length. Let the story breathe.

## Story shape (follow the arc, don't label the sections)

1. **Hook** — Open on a concrete moment: the alert, the failing deploy, the weird log line, the user report. No preamble like "In this post I will…" (roughly 1–2 paragraphs)
2. **Context** — Enough background that a new reader understands the system and why this mattered. Keep it brief. (1–2 paragraphs)
3. **Investigation** — The heart of the post. Walk through how you narrowed it down step by step. Include dead ends or false leads if the evidence mentions them. Show *thinking*, not just the final command. (a few paragraphs — the longest section)
4. **Fix** — What actually changed and why it worked. Use real commands, config snippets, or code from the evidence. Explain the mechanism, not just the diff. (2–3 paragraphs)
5. **Close** — One or two sharp takeaways tied to *this* incident, plus anything you'd do differently next time. No generic "always monitor your systems" unless the evidence supports it. (1–2 paragraphs)

## Use the evidence

- Treat the captured material as **source notes**. Pull in filenames, error messages, metrics, and decisions that appear there.
- **Do not invent** tools, timelines, root causes, or team details that are not supported by the evidence.
- If something is unclear in the evidence, say so briefly ("I didn't capture the exact latency number") rather than making it up.

## Format

- Output **markdown only** — no wrapper like "Here is your blog post".
- Title: specific and human (e.g. "Why our nginx reload kept serving stale certs" not "A Comprehensive Guide to nginx").
- Use `##` headings sparingly — only where they help scanning. Avoid a rigid five-section outline.
- Code blocks only when they clarify the fix or the bug. A 5–10 min post can include a few short snippets where they earn their place.

## Do not sound machine-generated

Avoid these patterns entirely:

- "In today's fast-paced world…", "Let's dive in", "In conclusion", "It's worth noting"
- Opening with a definition of the technology
- Bullet lists for every paragraph (lists are OK for commands or a short recap at the end)
- Generic lessons ("communication is key", "test in staging")
- Repetitive section openers ("Next, we will…", "Moving on to…")
- Title Case On Every Heading
- Overly polished corporate marketing tone

Write the post. Make it something you'd actually publish on your personal or team blog.
