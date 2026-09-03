# Ports

The ledger is `catalog/ports.md`, generated from `catalog/ports.yaml` and never
hand-edited. It sits outside `docs/`, so it is linked by URL rather than by a
relative path: a `../../` link escapes `docs_dir` and TechDocs renders it as a
dead link in the portal while the file is perfectly present in the repo.

- The ledger: [`catalog/ports.md`](https://github.com/chidionyema/idp/blob/main/catalog/ports.md)
- The rule, and how to declare a port: [ports](../onboarding/ports.md)
- The gate that refuses an undeclared port or probe: `bin/port-gate`
