# Demo: an agent runs a command with no shell

This is the execution door in operation. An agent on this estate has no `bash`; it submits work to
the executor daemon and reads the answer back. The whole round trip takes milliseconds to dispatch
and is bounded at 60 seconds of running.

Watch it from a terminal first, because the same daemon answers both ways.

Submit a command. It returns a job id immediately — it does not wait:

```
$ bin/idp-exec python3 -c "print('THE_DOOR_IS_LIVE')"
Dispatched. job_id: exec-1789305181-2
ceiling: 60s (enforced by the daemon, not by this tool)
Read it with read_job job_id="exec-1789305181-2".
```

Read it back. This is where the truth is:

```
$ bin/idp-exec --read exec-1789305181-2
{
  "found": true,
  "job_id": "exec-1789305181-2",
  "state": "finished",
  "exit_code": 0,
  "ceiling_sec": 60,
  "log": "THE_DOOR_IS_LIVE\n"
}
```

Ask what would happen without running anything:

```
$ bin/idp-exec --simulate sleep 900
REFUSED: this command waits on something outside the process; the executor runs work,
it does not park an agent
```

Ask for a ceiling above 60, in any spelling, and it is refused at the door:

```
$ bin/idp-exec --ceiling 2m make
REFUSED: ceilings above 60s are not available in any spelling
```

Now the same two steps from inside an agent session, which is the case that matters — the agent has
no shell at all, only these two tools:

```
execute_command({ command: "git log --oneline -3", cwd: "/Users/chidionyema/dev/code/idp" })
  -> { ok: true, job_id: "exec-1789305251-4" }

read_job({ job_id: "exec-1789305251-4" })
  -> { state: "finished", exit_code: 0, log: "d2421328 zone: read it, do not type it ...\n..." }
```

Finally, ask the estate where its own boundary stands:

```
$ bin/idp-executor-status
daemon:    MEASURED_OK   listening on /Users/chidionyema/.estate/executor.sock, ceiling 60s
boundary:  UNKNOWN       the agent's own uid can still rewrite:
    .../platform/executor/daemon.py             owner=501 mode=0644
    .../bin/exec-daemon                          owner=501 mode=0755
    .../Library/LaunchAgents/ai.estate.executor.plist owner=501 mode=0644
```

`boundary: UNKNOWN` is the tool telling the truth. The daemon applies the ceiling; the agent's own
uid can still rewrite the files that run it. That gap is named here rather than left to read as a
green it cannot support.
