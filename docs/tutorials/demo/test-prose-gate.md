# Demo: The prose-pin gate refuses a theatre test

The gate that keeps string-pinning tests out of the suite, shown refusing one and passing
one in under a minute.

## Run it

```
bin/test-prose-gate tests/fixtures/prose-pin/bad.py
```

The bad fixture holds a test function whose every assertion checks that a file contains an
exact sentence. The gate exits non-zero and names the function and the reason.

```
bin/test-prose-gate tests/fixtures/prose-pin/good.py
```

The good fixture holds a test that runs a command and asserts its exit code and parsed
output. The gate exits zero and says nothing.

## What you just saw

A test that pins wording fails when someone rewords a comment and passes when the behavior
breaks — the opposite of what a test is for. The gate reads each test function's assertions:
when every one of them is a string-membership check against file text, the function is
refused. A function with even one behavioral assertion passes. The continuous-integration
run applies the same scan to every test file in the repository, so a refused shape cannot
merge again.
