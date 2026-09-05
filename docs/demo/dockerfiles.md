# Demo: dockerfiles

`bin/dockerfiles` is the one list of estate images in this repository (ruling
R24). It finds every `Dockerfile` and `<name>.Dockerfile` under the tree, names
each by its stem or its directory, and prints one line per image:

```
$ bin/dockerfiles
estate-mcp mcp/estate-mcp.Dockerfile mcp
```

`--json` prints the same rows as a JSON array, which is the shape
`.github/workflows/build-multiarch.yml` consumes to build a matrix:

```
$ bin/dockerfiles --json
[{"name":"estate-mcp","dockerfile":"mcp/estate-mcp.Dockerfile","context":"mcp"}]
```

One path is excluded on purpose:
`backstage/packages/backend/Dockerfile`, the upstream Backstage scaffold,
because it needs a host `yarn build` and the repo root as context rather than
fitting this repository's build shape (tracked as idp#29).

There is no failure mode of its own — an empty repository prints nothing and
exits 0. What guards this list is `bin/multiarch-gate`, which fails if any
Dockerfile-shaped file in the tree is not one of the rows printed here, so an
image cannot dodge R24 by a file naming trick.
