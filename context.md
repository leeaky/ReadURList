# context.md — ReadURList

## One-line pitch
Saved URLs become a personal knowledge corpus. The system reaches out at unpredictable moments with genuine connections and tensions between things you've saved, and you can converse with the corpus at any time — dialogue with your own accumulated thinking, not another read-later graveyard.

## What this is NOT (anti-goals)
- Not a read-later app. Reading the original article is optional. The summary and dialogue extract the value; unread ≠ failure.
- Not a browsable library. V1 has no passive UI — chat is the only surface.
- Not a recap machine. A ping that merely restates what the user already saved is noise. Every ping must contain something the system *did* with the corpus: a connection, contradiction, extension, or open question.
- Not clickbait. Hooks must be genuine intrigue, never manufactured. Test: after reading the full analysis, does the teaser feel accurate? If not, it oversold.

## Core insight / why this exists
Read-later apps die because saving is satisfying and retrieving never happens — the archive becomes a guilt pile. This product inverts the direction: the system pushes value to the user through variable-timing pings, and the corpus doubles as an answer engine you talk to. Randomized timing creates a variable-reward loop, but the reward must be real or the user mutes the bot within weeks.

## Core loop
1. **Capture**: User submits a URL in chat.
2. **Ingest**: The article's content is extracted, summarized, and its key claims identified and stored.
3. **Connect**: Each new item is compared against the existing corpus. The goal is claim-level relationships — contradicts, extends, answers — not mere topical similarity.
4. **Ping**: At random-ish intervals, and ONLY when a genuine hook exists, the system sends: a one-line genuine tension or connection, a short analysis, and one question that invites a reply. Never a dead-end summary.
5. **Converse**: The user replies in the same thread and can ask anything of the corpus. Answers cite saved sources with links.

## Critical design rules
- **The empty ping is the mute button.** If nothing connects, don't ping. Hold boring or orphaned items until a real connection appears; re-evaluate as new items arrive.
- **Similarity ≠ relationship.** "Same topic" is shallow. The value is comparing actual claims across items and labeling the relationship. This is the hardest and most valuable component of the system; expect most iteration effort here.
- **Hook framing**: state the genuine tension or connection in one line — never "write an irresistible teaser."
- **Every ping ends with a question** that demands a reply — a tension, a contradiction, an open thread.
- **Save-time acknowledgment stays short** (title + one-line summary). Delivering the analysis at save time cannibalizes the ping's payload.
- **Cold start is expected.** With few items, connections are sparse and questions may go unanswered. Rare early pings are correct behavior, not a bug. If the corpus can't answer a question, say so plainly — never present outside knowledge as if it came from the corpus.

## Ping selection principles
- Prefer stronger relationship types (contradiction > answers > extends > merely related).
- Prefer items never surfaced before.
- Prefer connections that span time (something old ↔ something new).
- Cap frequency; unpredictable timing within reasonable hours; silence when no hook qualifies.

## Success metric (personal)
Week two: does the user reply to pings, or mute the system? Replies = alive. Mute = the hooks weren't genuine — fix connection quality before adding anything else.

## Deliberate V1 omissions
Web UI, multi-user, auth, tags/folders, highlights, non-article ingestion (PDF/video), spaced repetition, export. All deferrable; none block the core loop.
