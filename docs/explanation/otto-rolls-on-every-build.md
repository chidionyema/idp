# Otto rolls on every build

For days, work merged for Otto and the running pod never changed. The cause was one line:
the Otto pod's version tag was bumped by hand, and the hand never bumped it. Every other
rolling service in the estate has an automation entry that rewrites its tag on every build;
Otto's file carried a comment saying to bump it by hand "until this lane earns its own
policy." Nobody did, so the pod served an old build while the new builds piled up unreleased.

The fix reuses the automation that already exists. Otto runs the same container image as the hermes gateway
workload, so the tag line in `platform/otto-golden/kustomization.yaml` now carries the same
marker as `platform/hermes-agent/kustomization.yaml`: the image automation finds the marker,
writes the newest build's tag, and the update lands as an ordinary pull request that merges
itself when green. From this change on, every merged build of that shared image rolls the Otto
pod with no hand involved.

The lesson this page exists to keep: a workload whose version is bumped by hand is a workload
that does not ship. If a tag line has no automation marker, the work behind it is parked, not
released.
