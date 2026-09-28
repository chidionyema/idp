# Otto's registration checker: Asking Telegram, not guessing

The founder's agent Otto talks to Telegram through a webhook: Telegram is told one web address,
and it delivers every message to that address the moment it arrives. If that address is ever
wrong, or Telegram loses track of it, messages pile up on Telegram's side and nobody notices
until a person tries the bot and gets silence.

This checker removes the guessing. Every five minutes it asks Telegram itself — the same
question Telegram's own support page tells a developer to ask, "what web address do you have on
file for me, and how many messages are waiting behind it" — and turns the answer into two
numbers anyone can read on a dashboard:

- **Is the door registered.** One or zero. One means Telegram has a web address on file and
  the checker could reach Telegram to confirm it. Zero means either Telegram has no address on
  file, or the checker could not confirm it — either way, the honest state is "not registered,"
  never a guess.
- **How many messages are waiting.** A count. Zero is healthy. A number that keeps climbing over
  several checks means messages are arriving and nothing is answering them, well before a
  person notices the bot has gone quiet.

## Why ask Telegram instead of trusting our own record

Our own systems can believe a web address is registered when it is not — a typo, an expired
setting, a change nobody told this side about. Telegram's answer is the one fact that cannot be
wrong from our side, because Telegram is the one holding the record. This is the same reasoning
behind every other proof this platform keeps: read the fact from the source that owns it, never
from a summary of what we think it should be.

## What it never does

- It never prints or stores the bot's private key. It reads the key from the same protected
  location the bot itself already reads it from, uses it for one question, and throws it away.
- It never creates a second copy of that key. There is one key, kept in one place, read by both
  the bot and this checker.
- It never guesses a channel it was not told about. Today there is one bot on one messaging
  channel; when a second messaging channel or a second customer's bot is added, this checker
  gains a second row of numbers, not a second file.

## Where the numbers go

The two numbers travel to the same place every other reading in this estate already goes — one
shared collector that the operations dashboard already reads from. Nothing new was built to
carry them; they ride the road that exists.

## If the numbers turn red

A "not registered" reading, or a waiting count that keeps climbing, is loud on its own: the check
run fails and is visible wherever failed scheduled work is watched, with no dashboard colour to
misread. The fix is always the same first step — ask Telegram directly with the same question
this checker asks, confirm the web address on file is the right one, and re-register it if not.
That step is a person's call, never this checker's; it only ever reports what it found.
