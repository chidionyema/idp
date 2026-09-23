# Getting picture evidence for a portal change

Any change to what the founder sees in the portal needs picture evidence before it is released. The camera is the hourly sign-in drill; you never sign in yourself and you never handle the drill credential.

## Steps

1. Push your branch. The drill script and its workflow ride with it, so the branch version is what runs.
2. Dispatch the drill against your branch, naming the pages your change touches:

       gh workflow run login-drill.yml --ref <your branch> -f evidence_paths=/path/one,/path/two

3. Wait for the run to go green, then download the pictures:

       gh run download <run id> --name login-drill-home

4. Check each picture in `shots/` with your own eyes. The drill has already refused blank pages, but you are the second angle: the picture must show the change you made.
5. Commit the pictures to your branch and send them to the founder on the agreed channel, pinned, before asking for a release.

## When it goes red

A red `evidence` stage means the page never answered or never painted words. That is a real defect on the page, not a camera problem: fix the page, never the check.
