# The portal, locally: what actually has to be true

**Written 2026-09-18**, after three separate faults in one afternoon which all presented to the
founder as *"the page is broken"* and all of which were the **running setup**, not the code.

This file exists because the previous documentation said one sentence:

> "Locally it is `yarn start` in `backstage/` (frontend on 3100, backend on 7107)."
> — `docs/how-to/onboarding/portal.md`

That is **two of the three processes**, with no mention of config reload, of the third process,
or of the sign-in wall. Every fault below was invisible in that sentence, and every one of them
cost real time.

## The command that replaces it

```
bin/idp-portal            # starts all three, waits until each really answers, prints the URL
bin/idp-portal --check    # which pieces are up, changes nothing
bin/idp-portal --restart  # restart the frontend, for an app-config.yaml change
```

## The three processes, and why each one matters

| process | port | what it is | what breaks without it |
|---|---|---|---|
| `bin/serve-fleetview` | 18790 | the Python fleetview backend | every board read fails; the page shows an **empty board**, not an error |
| `yarn workspace backend start` | 7107 | Backstage's own server | nothing loads; `/api/proxy/*` is unreachable |
| `yarn workspace app start` | 3100 | the portal you open | — |

Started in that order, because each depends on the one above it. The frontend proxies
`/api/proxy/fleetview/*` to 18790, so a down plugin is not a visible failure — it is an empty
board, which is the failure mode that wasted the most time.

## The four traps, each measured

### 1. `app-config.yaml` is read at START, and a running server never sees an edit

Measured: the frontend was started at 16:18; `app-config.yaml` was edited at 17:36; the served
bundle still contained the old value at 17:45. **Roughly ninety minutes of an edit that was
simply not in effect**, and nothing anywhere said so.

```
bin/idp-portal --restart
```

This is the reason that flag exists. It is the single most confusing behaviour in the local
setup: the file is right, the code is right, and the page is wrong.

### 2. `/fleet` is behind sign-in, and that is what "flashes and breaks" means

A first visit, or any signed-out visit, renders the **guest sign-in wall** — not the board.
Verified through a real browser:

```
before Enter:  body = "Bytesync | Guest | Enter as a Guest User. | ... | Enter"
after Enter:   23 session cards, full nav, board present
```

Nothing crashes, and no console error is raised. It reads as a broken page because the wall
renders and then nothing appears to happen. **Press Enter.** That is the whole fix.

The session is durable — `localStorage` keeps `@backstage/core:SignInPage:provider`, and reload
and a new tab both stay signed in. It is *not* a persistence bug; a previous changelist invented
a fix for one and had to delete it.

### 3. The app is called **Bytesync** on purpose

`app.title` and `organization.name` read `Bytesync`, decided in
`docs/decisions/portal-defects-crew612.md`:

> "**Brand.** `app.title` and `organization.name` in `backstage/app-config.yaml` read Mumchimp;
> the portal is the estate portal, not the store. Both now read Bytesync."

The parent-company name is an open decision (`crew#691`), and
`backstage/org/catalog-info.yaml` deliberately refuses to guess one until it lands. An agent
read "Bytesync" as a stray vendor default and changed it to "Estate" on 2026-09-18. **That was
wrong and was reverted.** Known cosmetic bug, not fixed here: the browser tab reads
`Bytesync | Bytesync`, because Backstage's `<page> | <app.title>` template and the home page's
own title are the same word.

### 4. A `/stream` 401 on first load is normal

The board opens an SSE connection on first render, which can happen while the visitor is still
on the sign-in wall. The endpoint is **not** misconfigured: with a real token it answers 200
(measured: `sessions` 200, `stream` 200, `graph` 200). The 401s in the backend log are that
ordering, and they stop once signed in.

## How to verify any of this

A `curl` proves the API answers and says **nothing** about what a person sees. Three times this
day a claim was made from a terminal and was wrong. The only instrument that has ever found the
truth about this page is a real browser:

```js
// node, from backstage/ (playwright-core resolves from there, not from /tmp)
const b = await chromium.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: true,
});
const p = await b.newPage();
const errs = [];
p.on('pageerror', e => errs.push(e.message));
p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
await p.goto('http://localhost:3100/fleet', { waitUntil: 'load' });
await p.waitForTimeout(6000);
const wall = await p.$('button:has-text("Enter")');
if (wall) { await wall.click(); await p.waitForTimeout(9000); }
console.log(await p.evaluate(() => ({
  title: document.title,
  board: !!document.querySelector('[data-testid="fleet-sessions"]'),
  cards: document.querySelector('[data-testid="fleet-sessions"]')?.children.length,
})));
console.log('errors:', errs);
```

That is the check. Run it before claiming the portal works.

## The one-line summary

**Three processes, in order; a restart for config edits; and the word Enter on the first visit.**
Everything else on this page is the evidence for those three.
