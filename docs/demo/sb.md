# Demo — the sovereign bus (`sb`)

Recorded 2026-08-25 from `scratchpad/phase1.sh` on commit 3141eeb. Tokens and keys are never printed.

Start the engine, then a session, and read it back:

    $ bin/sb up
    {'temporal': 'started pid=83662', 'worker': 'started pid=83669'}
    $ bin/sb start --runner echo --task 'count to 5' --json
    $ bin/sb show sb-… --json
    status=done step=1 budget_remaining=998

Stop a session while the worker is dead. The stop is durable: the worker picks it up when it returns.

    $ bin/sb stop sb-… --by founder --reason 'laptop asleep' --json
    ok=True
    $ bin/sb show sb-… --json
    status=stopped stopped_by=founder

A session that needs a dangerous command waits for a decision. Deny, approve, or say nothing:

    status=waiting asking=git push --force
    status=denied
    status=done
    status=waiting

The budget wall halts a session at zero tokens and signs the halt:

    $ bin/sb start --runner burn --task burn --budget 100 --json
    status=halted reason=budget budget_remaining=0
    kind=halt counter=12 backend=keychain

The receipt chain catches an edit, a deleted middle, and a cut-off tail:

    $ bin/sb audit --verify --json
    ok=True count=12
    ok=False first_broken_counter=3
    ok=False

Every setting is one table:

    $ bin/sb config --json | python3 -c '…print(len(d))'
    180
    $ bin/sb config --lint
    0

The cockpit serves the same sessions the CLI lists, and refuses a bad Telegram signature:

    healthz: ok
    sessions match sb list
    bad initData -> 401
