# readurlist — Build Map

**Status:** signed off 2026-10-31

**Sources (the authority for this map):**
- **Brainstorm** = `C:/dev/ai-factory/knowledge/brainstorms/2026-10-30-readurlist.md` (ai-factory `main`, commit `41c1e16`). Cited as "Brainstorm §x".
- **Chat** = the owner's answers in the build-map chat of 2026-10-31, quoted where used. Cited as "Chat 2026-10-31".
- **Context** = `context.md` in this repo. Cited as "Context §x".
- **README** = `README.md` in this repo. Cited as "README §x".
- **R-0003** = `C:/dev/ai-factory/knowledge/rulings/R-0003-untrusted-input.md`. Cited as "R-0003 layer n".
- **Source-conflict rule (owner, 2026-10-31):** where Context or README disagree with the Brainstorm or the owner's answers in this chat, the Brainstorm and the chat win. Context still holds where they are silent (single user, no corpus Q&A, not a recap machine). Every disagreement is still listed in the map so the owner can see what changed. Owner's words: "A".

## Goal and use case

Map what readurlist does today against what it's for, then fix what isn't working:

1. **Time.** What I'm offered fits the time I actually have to read, not a fixed daily list.
2. **Clear scoring.** I can see why a link appears in my list and why it drops off.
3. **Two tracks.** Dense papers get a different track from a casual read on a tram, and phone reading is treated differently from PC reading.

Not in this build: capturing and organising takeaways. That is a separate piece shared with ms-brain, clipr and im-agent. The map only notes where it would connect.

Goal: owner, 2026-10-31, "Yes".

**Day-to-day use:**

- **Saving:** through the day I paste links into Telegram from whatever device I'm on, and glance at the reply to check the save worked. Owner, 2026-10-31: "as described".
- **Telegram daily list:** once a day Telegram sends a suggested reading list for the day in two sections, **short** and **long**, with a note at the bottom listing the links that have fallen off and why. Owner, 2026-10-31: "still produce a suggested reading list for the day but with two sections - short and long, and a note at the bottom listing the urls that have falled off and why". (Replaces the earlier "nudge, no list" wording; first answer that day was "B: keep a nudge".)
- **Short gap on my phone** (tram, queue, about 10–20 min): if I have the bandwidth I open the website's Today page and pick one or two quick reads. Owner, 2026-10-31: "no need to send message to telegram. If I have the bandwidth, I will look at the website itself at the today page"; confirmed "yes".
- **Longer block at my PC:** I go to the website myself for a dense read. Owner, 2026-10-31: "i will go to website myself".
- **Why a link is picked or dropped:** wanted, but how to show it is not settled. Owner, 2026-10-31: "not sure how you intend to show this". See Q1.
- **Once in a while:** All, Organize and Unfetched to tidy up, as today. Owner, 2026-10-31: "yes".

Day-to-day use confirmed line by line as quoted above; the "why" display is open (Q1).

Confirmed by the owner on 2026-10-31.

## Big picture

You save links in Telegram. Each link is fetched and read by a language model that has no tools and must answer in a fixed form; it writes a short summary, tags, and (new) how much effort the piece takes. Every day the tool scores the unread pile in a way it can explain, splits it into a short section and a long section, and notes what fell off and why. You see that list in Telegram and on the website's Today page, and you tidy the library on the website now and then. Takeaways (what you learned from a read) are a separate build; they would connect at the moment you mark something read.

**Stages are the order things get built, not how the finished tool runs.**

| # | Stage | Depends on |
|---|---|---|
| 1 | Save links from Telegram | — |
| 2 | Read each page safely | 1 |
| 3 | Fill in pages that couldn't be fetched | 2 |
| 4 | Tag each item by effort | 2 |
| 5 | Score the pile in a way you can follow | 2, 4 |
| 6 | Build the day's list: short, long, fallen off | 4, 5 |
| 7 | Today page on the website | 6 |
| 8 | Telegram daily list | 6 |
| 9 | Library tidy-up (All, Organize, Unfetched) | 2 |
| 10 | Is it working? | 6, 7, 8 |

## Stages

### Stage 1 — Save links from Telegram
- **What gets built:** You paste one or more links into a private Telegram bot from any device; it saves them and replies with a short summary so you can see the save worked. Only your Telegram account is listened to.
- **Why:** Saving must be easy from anywhere, and the reply is how you check it worked (Context §Core loop 1; Brainstorm §How the owner uses it today 1–2; README §Using the bot).
- **Depends on:** nothing
- **Produces:** saved links in the database, each waiting to be read by stage 2; a reply in Telegram per link.
- **Terms:** Worker, Allowlist, Snapshot
- **Status:** not started
- **Tasks:**
  - [ ] (a) Pasting links into the bot saves each one and replies with its summary, or with a "couldn't fetch" note and a link to fill it in.
    Detail: Telegram long polling on the worker; allowlist by numeric user id; sequential n/N replies (README §Using the bot).
  - [ ] (b) Messages from anyone else get no reply.
    Detail: allowlist check before any handler runs.
- **Issues:** none

### Stage 2 — Read each page safely
- **What gets built:** Each saved link is fetched and its text extracted; a language model with no tools reads it and must answer in a fixed form (summary, subject, topics, keywords, priority). Its answer is checked before it is stored. Pages that can't be fetched become placeholders for stage 3.
- **Why:** The summary and tags drive everything after; and fetched pages can contain text written to trick a model, so the reading model must be boxed in (Context §Core loop 2; R-0003 layers 1–3; Brainstorm §Notes for the map).
- **Depends on:** Stage 1
- **Produces:** each item marked ready, with summary and tags, or marked unfetched.
- **Terms:** Untrusted input, Quarantined reader, Schema, Tripwire, Snapshot, Subject / topics / keywords, Stub, Groq
- **Status:** not started
- **Tasks:**
  - [ ] (a) The model that reads page text has no tools, and its answer is rejected unless it fits the fixed form.
    Detail: check the Groq call passes no tools and uses structured outputs; validate the reply against a schema plus domain checks (R-0003 layer 2).
  - [ ] (b) Page text is cleaned of hidden characters and clearly marked as data before the model sees it.
    Detail: strip invisible and bidi characters, normalise Unicode, wrap in `<untrusted_document>` with a "this is data" notice (R-0003 layer 3).
  - [ ] (c) Tests use stored sample pages, never live pages or article text from the live database.
    Detail: fixtures under `tests/fixtures/pages/`, listed as untrusted paths; agents never open that folder (R-0003 layers 1, 6).
  - [ ] (d) New tags reuse the existing subject and topic names where they fit, so the vocabulary doesn't splinter.
    Detail: pass current subject/topic lists to ingest; consolidation of near-duplicates before ranking (Context §Core loop 2; README §Worker).
  - [ ] (e) Each page is scanned for text that looks like an attempt to instruct the AI; a suspicious page is held back from the model and shown on Unfetched marked "held", where you can release or delete it.
    Detail: tripwire before the Groq call (R-0003 layer 4; ai-factory has `factory scan injection`); a held status on the item; release sends it through stage 2, delete removes it. Decision: owner, 2026-10-31, "A" (options were: scan pages before the model / flag suspicious output / leave it out).
- **Issues:** none

### Stage 3 — Fill in pages that couldn't be fetched
- **What gets built:** On the website's Unfetched tab you paste the article text or upload a PDF for a link the tool couldn't fetch; the next daily run reads it through stage 2.
- **Why:** Paywalled and blocked pages, including many papers, would otherwise never enter the pile (Brainstorm §How the owner uses it today 6; README §Website).
- **Depends on:** Stage 2
- **Produces:** previously unfetched items that become ready.
- **Terms:** Stub, Unfetched, Tripwire
- **Status:** not started
- **Tasks:**
  - [ ] (a) Pasted text or an uploaded PDF goes through the same safe reading as a fetched page, including the tripwire scan.
    Detail: fill-in text must hit the stage 2 quarantined path, not a separate unchecked one.
  - [ ] (b) Pages held by the tripwire appear here marked "held", with release and delete.
    Detail: from the stage 2 (e) decision, owner 2026-10-31.
- **Issues:** none

### Stage 4 — Tag each item by effort
- **What gets built:** Each item gets an effort label, short or long, with an estimated reading time, so a dense paper is never offered for a tram ride.
- **Why:** Dense papers and quick articles need different tracks, and the daily list should fit the time you have (Brainstorm §What isn't working 1, 3; Chat 2026-10-31).
- **Depends on:** Stage 2
- **Produces:** an effort label and minutes estimate on every ready item, for stages 5 and 6.
- **Terms:** Effort label, Reading time
- **Status:** not started
- **Tasks:**
  - [ ] (a) Every ready item shows short or long and an estimated reading time.
    Detail: length decides, not density (owner, 2026-10-31: "short, long, short" for opinion piece / 30-page paper / 1,200-word proof post). Minutes from word count at about 230 words a minute; short = under 15 min (about 3,500 words), long = 15 min or more. Owner, 2026-10-31: "B: 15 min" (options were 20 / 15 / 10 min).
  - [ ] (b) Items saved before this stage get the label too.
    Detail: one-off backfill over existing ready items.
- **Issues:** none

### Stage 5 — Score the pile in a way you can follow
- **What gets built:** A score for each unread item made of a few named parts, each of which can be shown in a short sentence; the tool keeps each day's scores so it can say what changed.
- **Why:** The current scoring "doesn't work for me": it isn't clear why links pop up or drop off (Brainstorm §What isn't working 2). Context's weights (subject demand 45%, recency 20%, path novelty 20%, model priority 15%) are replaced here under the source-conflict rule (Context §Ranking).
- **Depends on:** Stages 2, 4
- **Produces:** a score per unread item with its reasons, and yesterday's scores to compare against, for stage 6.
- **Terms:** Unread queue, Score, Ranking weights, Subject demand, Recency, Fallen off
- **Status:** not started
- **Tasks:**
  - [ ] (a) Each unread item's score breaks into a few named parts you can read.
    Detail: two parts: subject demand 65, recency 35 (out of 100); path novelty and model priority dropped. Owner, 2026-10-31: "A" (options were: drop model priority only, 50/25/25 / keep subject demand and recency only, 65/35 / keep all four). Known trade-off, accepted with the choice: nothing stops several picks like ones just read. Keep scoring deterministic so reasons stay true. Each pick gets a one-line reason naming its biggest part, plus the points per part; each fallen-off link gets its main cause (read / skipped / outscored by newer saves / subject already has two picks) plus points before and after (Q1, owner 2026-10-31).
  - [ ] (b) The tool remembers yesterday's list so it can say why something left it.
    Detail: store each day's picks and scores.
  - [ ] (c) A restored item counts as freshly saved: its recency starts again from the day you restored it.
    Detail: recency uses the later of saved date and restored date. Owner, 2026-10-31: "I would suggest if restored, the date restarts to restoration date".
- **Issues:** none

### Stage 6 — Build the day's list: short, long, fallen off
- **What gets built:** Each day the tool picks a short section and a long section from the scored pile, and a list of links that were on yesterday's list but aren't today, each with a reason.
- **Why:** Digest by effort is the agreed direction, "but this is not ideal yet" (Brainstorm §What isn't working; Chat 2026-10-31). Context's single top-5 list with at most two per subject is replaced under the source-conflict rule (Context §Ranking).
- **Depends on:** Stages 4, 5
- **Produces:** the day's list, for the Today page (stage 7), Telegram (stage 8) and the success check (stage 10).
- **Terms:** Daily job, Effort label, Fallen off, Skip
- **Status:** not started
- **Tasks:**
  - [ ] (a) The day's list has a short section and a long section, each sized to an agreed amount of time.
    Detail: 3 short picks + 1 long pick. Owner, 2026-10-31: "A" (options were 3+1 / 2+1 / 5+2).
  - [ ] (b) Each dropped link is listed with its reason: you read it, you skipped it, or something else outscored it.
    Detail: compare today's picks to yesterday's (stage 5 b).
  - [ ] (c) The list still avoids being a recap of one save: it spreads across subjects.
    Detail: Context §What this is NOT, "not a recap machine".
  - [ ] (d) When no long read is ready, the long section says so and points to the papers waiting on Unfetched.
    Detail: e.g. "No long read ready. 6 papers are waiting on Unfetched" with a link. Owner, 2026-10-31: "A" (options were: that line / leave the section out / a 4th short pick) (Q8).
- **Issues:** none

### Stage 7 — Today page on the website
- **What gets built:** The website's Today page shows the short and long sections with each pick's reason, laid out to read well on a phone.
- **Why:** You'll open Today on the phone for a quick read and on the PC for a deep one (Chat 2026-10-31; Brainstorm §What isn't working 3).
- **Depends on:** Stage 6
- **Produces:** the page you use day to day.
- **Terms:** Effort label, Fallen off
- **Status:** not started
- **Tasks:**
  - [ ] (a) Today shows a short section and a long section, each pick with its reason in words, its points per part (always visible, no tap) and its reading time.
    Detail: Next.js `web/` Today tab.
  - [ ] (b) Today is easy to use on a phone screen.
    Detail: check at phone width.
  - [ ] (c) You can mark a pick read or skip it from Today.
    Detail: as today (README §Website).
  - [ ] (d) Today ends with a small Fallen off section: each dropped link with its cause in words and its points before and after.
    Detail: from stage 6 (b). Owner, 2026-10-31: "A" (options were: Fallen off section on Today / Telegram only).
- **Issues:** none

### Stage 8 — Telegram daily list
- **What gets built:** Once a day Telegram sends the day's list in two sections, short and long, with a note at the bottom listing links that fell off and why.
- **Why:** Owner, 2026-10-31: "still produce a suggested reading list for the day but with two sections - short and long, and a note at the bottom listing the urls that have falled off and why" (Chat 2026-10-31; replaces Context §Core loop 4 under the source-conflict rule).
- **Depends on:** Stage 6
- **Produces:** the daily Telegram message.
- **Terms:** Daily job, Fallen off
- **Status:** not started
- **Tasks:**
  - [ ] (a) The daily message has a short section, a long section and a fallen-off note.
    Detail: format the stage 6 list; at most once per day. Reasons in words only, no points, to keep it short on a phone (Q1, owner 2026-10-31: "B").
  - [ ] (b) The message has no buttons; you mark read or skip on the website.
    Detail: remove the Mark read / Skip inline buttons and their handlers' use in the daily list. Owner, 2026-10-31: "B" (options were keep both buttons / drop them) (Q3).
- **Issues:** none

### Stage 9 — Library tidy-up (All, Organize, Unfetched)
- **What gets built:** The website's All tab (filters, edit, mark read, skip, restore), Organize (merge stray labels, batch edits, oldest unread) and Unfetched stay as they work today.
- **Why:** Owner uses them once in a while and wants them kept (Chat 2026-10-31: "yes"; Brainstorm §How the owner uses it today 5–6; README §Website).
- **Depends on:** Stage 2
- **Produces:** a tidy library.
- **Terms:** Unread queue, Skip, Subject / topics / keywords
- **Status:** not started
- **Tasks:**
  - [ ] (a) All, Organize and Unfetched keep working as they do now, and also show each item's effort label.
    Detail: add effort label to cards and filters.
- **Issues:** none

### Stage 10 — Is it working?
- **What gets built:** A way for you to see whether the new list helps: how many picks you read, and whether the unread pile is shrinking.
- **Why:** Context's own success test: "Do digest picks get marked read, and does the unread pile shrink? If not, tune ranking before adding features" (Context §Success metric).
- **Depends on:** Stages 6, 7, 8
- **Produces:** a weekly line in Monday's Telegram list and a 7-day panel on Today.
- **Terms:** Unread queue
- **Status:** not started
- **Tasks:**
  - [ ] (a) Monday's Telegram list ends with one line on last week: picks read, picks skipped, and the unread pile then and now.
    Detail: e.g. "Last week: read 5 of 12 picks (42%, below half: tune the ranking). Skipped 3. Unread pile 140 → 142." Owner, 2026-10-31: "C" (options were Telegram line / Today panel / both) (Q5).
  - [ ] (b) Today shows the same numbers for the last 7 days in a small panel.
  - [ ] (c) The verdict is the read rate: working if you read at least half the picks shown; the pile size is shown for background only.
    Detail: read rate = distinct picks shown in the week that were marked read ÷ distinct picks shown. Owner, 2026-10-31: "A" (options were read rate ≥ half / Context's test as written / no pass mark) (Q9). Replaces Context §Success metric's pile test under the source-conflict rule.
    Detail: same counts as (a), rolling 7 days (Q5).
- **Issues:** none

## Blocks

None.

## Open questions

- **Q1 — How to show why a link is picked or dropped.** Brainstorm §What isn't working (2) says it isn't clear why links pop up or drop off. The owner wants the fallen-off links listed with a reason in the Telegram list, but is "not sure how you intend to show this" (2026-10-31). Resolved 2026-10-31: reasons in words and points, "A+B combination" (A = one plain line, B = points per part); then "B" for placement: Telegram shows words only, Today shows words and points always visible. Applied in stages 5, 7, 8. *Status:* resolved
- **Q2 — What counts as short or long, and how big is each section?** Brainstorm gives "quick reads and a deep read each day" and "about 10–20 min" for a phone gap, but no thresholds or section sizes. Affects stages 4 and 6. Part settled 2026-10-31: length decides, not density ("short, long, short"); short = under 15 min at about 230 words a minute ("B: 15 min"). Section sizes settled 2026-10-31: 3 short + 1 long ("A"). Applied in stages 4 and 6. *Status:* resolved
- **Q3 — Keep Mark read / Skip buttons in the Telegram list?** Context §Core loop 4 has them; the owner's description of the new list (2026-10-31) doesn't mention them. Resolved 2026-10-31: drop them ("B"); marking read and skipping happen on the website. Applied in stage 8 (b). *Status:* resolved
- **Q4 — Phone vs PC.** Brainstorm §What isn't working (3) says phone and PC reading differ. The owner's day-to-day answer is that both go through the same Today page (short on phone, long on PC). Assumed: one Today page with both sections, no device detection. *Status:* assumption
- **Q5 — How you'll see whether it's working.** Context §Success metric names the test but not where you read the result (a line in the Telegram list, a page, a weekly message). Resolved 2026-10-31: both, a line in Monday's Telegram list and a 7-day panel on Today ("C"). Applied in stage 10. *Status:* resolved
- **Q6 — Where takeaways would connect.** Out of scope (Brainstorm §Scope). The natural connection point is "mark read" (stages 7, 8, 9). *Status:* deferred (to the separate knowledge-organisation build)
- **Q7 — Context vs README wording: "topic demand" vs "subject demand".** Context §Ranking says topic demand 0.45; README §Worker says subject demand 0.45. *Status:* folded (into stage 5, which replaces the weights)

- **Q8 — What the list shows when there is no long read.** Found in the stage 6 check (2026-10-31): with all papers still unfetched, the long section is empty, and no source says what to show. Resolved 2026-10-31: show "No long read ready. N papers are waiting on Unfetched" with a link ("A"). Applied in stage 6 (d). *Status:* resolved

- **Q9 — What counts as "working".** Context §Success metric asks whether picks get read and the pile shrinks, but sets no pass mark, and the pile also grows with how much the owner saves, which says nothing about the list. Found in the stage 10 check (2026-10-31). Resolved 2026-10-31: read rate is the test, working if at least half the picks shown in the week are read; pile shown for background ("A"). Applied in stage 10 (c). *Status:* resolved

## Glossary

**Allowlist** — the one Telegram account the bot listens to; everyone else is ignored · README §Telegram bot setup · keeps the app single-user.
**Daily job** — the run once a day that reads filled-in pages, scores the pile and builds the list · README §Worker · stages 6 and 8 hang off it.
**Effort label** — new: short or long, with an estimated reading time · Brainstorm §What isn't working 3 · drives the two sections.
**Fallen off** — a link on yesterday's list that isn't on today's · Chat 2026-10-31 · you want each one listed with why.
**Groq** — the hosted service that runs the reading model · README §Models · page text is sent there, so R-0003 applies.
**Model priority** — the reading model's own guess at how important an item is; 15 of 100 points in today's score · Context §Ranking · dropped from the score in stage 5 (owner, 2026-10-31).
**Path novelty** — how different an item is from what you've read lately; 20 of 100 points in today's score · Context §Ranking · dropped from the score in stage 5 (owner, 2026-10-31).
**Quarantined reader** — a model that reads untrusted text with no tools and must answer in a fixed form that is checked · R-0003 layer 2 · the safety check for stage 2.
**Ranking weights** — how much each part counts in the score; today 45/20/20/15 out of 100, new 65/35 · Context §Ranking, owner 2026-10-31 · set in stage 5, tuned after stage 10.
**Recency** — how recently you saved an item; newer scores higher, 35 of 100 points · Context §Ranking · one of the two parts kept.
**Subject demand** — how many unread items share this item's subject; 65 of 100 points · Context §Ranking ("dense topics in the backlog") · the main part kept.
**Reading time** — estimated minutes to read an item · Brainstorm §What isn't working 1 · lets the list fit a 10–20 min gap.
**Schema** — the fixed form the model's answer must match (named fields of set types); answers that don't fit are rejected · R-0003 layer 2 · stops injected text from becoming instructions.
**Score** — one number per unread item that orders the pile · Context §Ranking · stage 5 makes it explainable.
**Skip** — take an item out of the unread queue without marking it read · Context §Ranking · one reason a link falls off.
**Snapshot** — the short AI summary saved with each link · Context §Core loop 2 · what you glance at to check a save worked.
**Stub** — a placeholder for a link that couldn't be fetched, waiting for you to paste the text · README §Using the bot · lives on the Unfetched tab.
**Subject / topics / keywords** — tags the reading model gives each item: one subject, a few topics, specific keywords for display only · Context §Ranking · subject spread keeps the list from being a recap.
**Tripwire** — a scan that scores a page for text trying to instruct an AI, and holds suspicious pages back before the model reads them · R-0003 layer 4 · added to stage 2 on 2026-10-31.
**Unfetched** — the website tab listing stubs, and (new) pages held by the tripwire · README §Website · where you fill in papers.
**Unread queue** — items that are ready and neither read nor skipped · Context §Ranking · the pile the daily list is drawn from.
**Untrusted input** — any text from outside, such as fetched web pages; treated as possibly hostile · R-0003 · why stage 2 is boxed in.
**Worker** — the always-on program on your machine that listens to Telegram, calls Groq and runs the daily job · README §Worker · stages 1, 2, 6, 8 run there.

## Check log

| Stage | What the owner explained back or predicted | Confirmed against | Date |
|---|---|---|---|
| 1 Save links from Telegram | Three links, third paywalled: "i will get 3 responses back - all saying that the link is saved but the first 2 will show a short summary and the 3rd will show a saved link but a short summary cannot be extracted and will be in unfetched". Matches; added: replies come in order labelled 1/3, 2/3, 3/3, and the third carries a link to the Unfetched page. | README §Using the bot ("Sequential n/N snapshots. Fetch/extract failure → stub + Unfetched link") | 2026-10-31 |
| 2 Read each page safely | Hidden white-on-white instruction. First answer: "hidden text is cleaned before the qroq model sees it so the hidden text mshould not work" (wrong: cleaning removes invisible characters, not colour-hidden text). Second answer: "the hidden line (white-on-white) can tell make it through as data which the model is less likely to obey. However, because of the wrapper, it cannot visit the site or send a message. Its impact is limited to text output". Matches, with one correction: the wrapper only makes obeying less likely; it is having no tools that stops visiting or sending, and "text output" includes the fields of the form, such as a priority of 5. | R-0003 layers 2–3 | 2026-10-31 |
| 3 Fill in pages that couldn't be fetched | 2 MB PDF uploaded at 2pm, daily job at 7am: "after the 7am daily job. A pdf or pasted text has to be inputted on unfetched and have the link queued to be processed before the job will pick it up". Matches; added: it is hidden from Today and All until then, `/digest` would bring it in sooner, and the job runs it through stage 2 including the tripwire, so it could come back "held". | README §Website ("Stubs are hidden from Today and All until ingest completes"), README §Using the bot | 2026-10-31 |
| 4 Tag each item by effort | 2,000-word opinion piece / 30-page paper with equations / 1,200-word maths-proof blog post: "short, long, short". Consistent with the sources (papers are the long track); the third answer shows length decides, not density, which the sources didn't settle. Fed into Q2. | Brainstorm §What isn't working 3 | 2026-10-31 |
| 5 Score the pile in a way you can follow | Yesterday's #3 gone, not read or skipped: "new articles of different subjects crowd out this pick / the pick was older / read similar articles recently". Matches all three (newer saves outscore it, recency fades, path novelty drops); added: the two-per-subject cap can also push it out when newer items in its own subject outscore it. | Context §Ranking | 2026-10-31 |
| 6 Build the day's list | Pile of 40 short (25 on one subject) and 0 long: "3 short 0 long". Matches on counts; added: the short section is 2 from the big subject (the two-per-subject cap stops a third) plus 1 from whichever other subject scores highest. The sources don't say what an empty long section should show; raised as Q8. | Context §Ranking (two-per-subject cap); stage 5 and 6 decisions of 2026-10-31 | 2026-10-31 |
| 7 Today page on the website | On the tram: "short section - long section. Both with reasons and reading times" (missed the always-visible points line from Q1, corrected); after Mark read: "one less". Matches: the pick leaves the unread queue and Today shows one fewer; the list is not refilled until the next daily job. | Context §Ranking (unread queue); README §Worker (ranking runs in the daily job); Q1 decision of 2026-10-31 | 2026-10-31 |
| 8 Telegram daily list | Yesterday A, B, C short and P long; read A, skipped B, saved 5 new short on a new subject. First answer: "3 new, P and C fallen off with reason" (wrong: the subject cap allows 2 new; P only competes with long items; A and B also fall off). Second answer: "short - 2 new + C, P stays, A & B fallen off but due to read or skipped". Matches (C stays unless another older item outscores it). | Context §Ranking (two-per-subject cap); stage 6 tasks (a), (b) | 2026-10-31 |
| 9 Library tidy-up | Skip P on All, then restore a month later. First answer: "to be honest, i do not know"; explained from the sources. Explain-back: "once skipped, the url goes to a skipped list on the website. It can be restored but the scoring is lower due to recency." Matches. Owner then asked for a change: "I would suggest if restored, the date restarts to restoration date" (added to stage 5 (c)). | Context §Ranking (skip leaves the queue without marking read); README §Website (Skipped filter, restore) | 2026-10-31 |
| 10 Is it working? | Week: 12 picks shown, 5 read, 3 skipped, 10 saved, pile 140 last Monday. First: "not sure i get the context of whether it is working"; explained (pile 140 + 10 − 5 − 3 = 142). Explain-back: "the pile did not shrink so no it did not work". Matches Context's test as written. Raised Q9: the pile measure mixes list quality with how much is saved. | Context §Success metric | 2026-10-31 |

## Code overlay

Owner's stance on existing code (2026-10-31): "A". Works in daily use but unvetted: trust behaviour, not design. Parts the owner uses daily count as built if they do what the map says; anything the map changed (scoring, the list, Telegram, safety) is wrong until shown otherwise.

Read on 2026-10-31 from commit `85b3803`, code only (no `.env`, no `web/.env.local`, no `tests/fixtures/pages/`, no live database). Tests not run: `uv run pytest -q` failed before running (it began resyncing `.venv` and hit a file locked by the worker); after the repair, `.venv\Scripts\python -m pytest -q` → "No module named pytest" (dev extras not installed by `uv sync`).

| Stage | Status | Evidence | Gaps against the map | Proposal |
|---|---|---|---|---|
| 1 Save links from Telegram | built | `src/readurlist/bot/handlers.py`, `src/readurlist/ingest/__init__.py`, `src/readurlist/ingest/extract.py` | none; owner uses it daily and it answered `/start` on 2026-10-31 | keep |
| 2 Read each page safely | partly built | `src/readurlist/llm/groq_provider.py` (no tools passed; `json_schema` with `strict: True`), `src/readurlist/prompts.py`, `src/readurlist/ingest/summarize.py` (clamps priority 1–5, caps lists) | (b) no invisible-character cleaning and no "this is data" wrapper: page text goes straight after "Article text:"; (c) no stored sample pages (0 files tracked under `tests/fixtures/pages/`); (e) no tripwire, no "held" status; checks beyond the schema are only clamps | fix |
| 3 Fill in pages that couldn't be fetched | built | `web/app/actions.ts` `submitArticleBody`, `web/lib/pdf.ts`, `src/readurlist/ingest/complete.py` | uses the same reading path as stage 2, so it inherits stage 2's gaps; no "held" display (b) | keep; gaps close with stage 2 plus (b) |
| 4 Tag each item by effort | missing | none. Full page text is already stored per item (`items.extracted_text`), so word counts need no refetch | everything | build |
| 5 Score the pile in a way you can follow | partly built | `src/readurlist/rank/score.py` (45/20/20/15, two-per-subject cap, template reasons), `daily_picks.score` | old weights; only the total is stored, not parts; restore keeps the original save date (`web/app/actions.ts` `setSkipState` only clears `skipped_at`; recency uses `created_at`) | rebuild `score.py` (small, and the formula is replaced); keep the cap |
| 6 Build the day's list | partly built | `src/readurlist/rank/run.py` `persist_ranking` (top 5, one list; past days kept in `daily_picks`; today's rows deleted and rebuilt on each run) | no short/long sections, no fallen-off list, no empty-long message | fix |
| 7 Today page on the website | partly built | `web/app/page.tsx`, `web/components/TodayList.tsx`, `web/components/ItemCard.tsx`, `web/app/globals.css` (phone rules at 600px and 900px) | no sections, points, reading time or Fallen off section; the blurb (`web/lib/ranking-copy.ts`) describes the old formula | fix |
| 8 Telegram daily list | partly built | `src/readurlist/rank/run.py` `format_digest`, `run_digest_job`; button handlers in `bot/handlers.py` | one list with Mark read / Skip buttons; no sections or fallen-off note; `/start` text mentions buttons | fix |
| 9 Library tidy-up | built | `web/app/all/page.tsx`, `web/app/organize/page.tsx`, `web/app/unfetched/page.tsx`, `web/lib/filters.ts`, `web/lib/organize.ts` | no effort label on cards or filters | keep, plus the label |
| 10 Is it working? | missing | none | everything | build |
| extra: website password gate | extra (called for by Context §What this is NOT, but no stage covers it) | `web/middleware.ts`, `web/lib/auth.ts`, `web/app/login/` | none | keep |
| extra: leftover similarity column | extra | `items.similar_to_item_id` in `src/readurlist/db/__init__.py` (unused since commit `781fc6c`) | dead code | flag; outside this build |
| extra: SQLite migration script | extra | `scripts/migrate_sqlite.py` | one-off tool, README documents it | keep |

Decision on stages 1–5 (owner, 2026-10-31): "Yes, all five" (1 keep, 2 fix, 3 keep, 4 build, 5 rebuild).
Decision on stages 6–10 and extras (owner, 2026-10-31): "Yes, all" (6 fix, 7 fix, 8 fix, 9 keep plus effort label, 10 build; password gate keep; similarity column flag only, outside this build; SQLite script keep).

## Sign-off

Owner's words, 2026-10-31: "A: sign off".

Signed off by the owner on 2026-10-31.
