# Picture evidence from the sign-in drill

The founder asked for picture evidence before any release that changes what he sees in the portal. This feature makes the hourly sign-in drill the camera: it signs in the way a person does, walks to the pages named in the request, waits until words have drawn on each one, and photographs them. A page that never answers or never paints fails the drill instead of producing a blank grey picture.

## See it work

Ask the drill to photograph a page from any branch:

    gh workflow run login-drill.yml --ref <branch> -f evidence_paths=/catalog/default/component/layer-hermes-agent

When the run finishes, download the pictures:

    gh run download <run id> --name login-drill-home

The `shots/` folder in the artifact holds one picture per requested page, named after the page. The run log carries one `shot` line per picture stating how many characters of text had painted before the photograph was taken.

## What it proves

Each picture shows the page as the signed-in drill user saw it, after the page painted. Because the drill fails when a page is blank, a picture existing at all is proof the page rendered with real content.

## Watch it

The machines record this demo from the real drill configuration on every relevant
push (`demos/drill-evidence.tape`), so the picture below can never show something
the software no longer does:

![The sign-in drill's shape and its passing test, recorded by the machines](../demos/drill-evidence.gif)
