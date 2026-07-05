# Write an engineering incident story

Turn the captured evidence below into a **markdown blog post** that reads like a real engineer wrote it after living through the problem — not like a summary bot filled in a template.

## Voice and tone

- Write in **first person** ("I noticed…", "We tried…") or a direct **we** if the work was clearly shared.
- Sound like **technical writing about an incident**: grounded, specific, a little tired-in-a-good-way honesty is fine.
- Assume the reader is a **practicing engineer** who has debugged production before. Skip basics they already know.
- Prefer **short paragraphs** and natural transitions. Vary sentence length. Let the story breathe.

## Story shape (follow the arc, don't label the sections)

1. **Hook** — Open on a concrete moment: the alert, the failing deploy, the weird log line, the user report. No preamble like "In this post I will…"
2. **Context** — Just enough background so the hook makes sense. One or two sentences, not a history essay.
3. **Investigation** — Walk through how you narrowed it down. Include dead ends or false leads if the evidence mentions them. Show *thinking*, not just the final command.
4. **Fix** — What actually changed. Use real commands, config snippets, or code from the evidence when available. Explain *why* the fix works, not only *what* changed.
5. **Close** — One or two sharp takeaways tied to *this* incident. No generic "always monitor your systems" unless the evidence supports it.

## Use the evidence

- Treat the captured material as **source notes**. Pull in filenames, error messages, metrics, and decisions that appear there.
- **Do not invent** tools, timelines, root causes, or team details that are not supported by the evidence.
- If something is unclear in the evidence, say so briefly ("I didn't capture the exact latency number") rather than making it up.

## Format

- Output **markdown only** — no wrapper like "Here is your blog post".
- Title: specific and human (e.g. "Why our nginx reload kept serving stale certs" not "A Comprehensive Guide to nginx").
- Use `##` headings sparingly — only where they help scanning. Avoid a rigid five-section outline.
- Code blocks only when they clarify the fix or the bug. Keep snippets short.

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
