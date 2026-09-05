# The estate catalogue, built into an image.
#
# WHY THIS EXISTS. Until 2026-08-24 the catalogue was started by `nohup yarn
# start` from bin/idp-up: a development server, on a laptop, under launchd. That
# has three properties a buyer's engineer finds in one sitting. It serves the
# webpack dev server, which refuses any Host header that is not the one in
# app.baseUrl -- measured the same day, the tailnet link returned 403. It binds
# whatever Node feels like: the app landed on [::1] and the backend on
# 127.0.0.1, two different address families for one product. And it cannot be
# deployed anywhere, so the k8s migration would have started from nothing.
#
# Founder directive, 2026-08-24: "we also cannot accept the brittle yarn start
# laptop hack ... containerize the application exactly as it will run in k8s".
# This is Phase 1 of that. Phase 2 is Kustomize manifests over THIS SAME IMAGE,
# and the interim is removed by deleting one compose file.
#
# WHY MULTI-STAGE AND NOT packages/backend/Dockerfile. The scaffolder's
# Dockerfile is a host build: it requires `yarn install && yarn tsc && yarn
# build:backend` to have been run on the machine first, with the same Node major
# as the image. Measured on this machine 2026-08-24: host node is v26.7.0, the
# image is node:24, and package.json declares `engines.node: 22 || 24`. The host
# build is therefore not runnable here at all, and better-sqlite3 is a native
# module, so a mismatch does not fail loudly -- it produces an image that
# crashes at require() time. Multi-stage puts the toolchain inside the build,
# where its version is a property of this file rather than of a laptop.
# It is the alternative Backstage documents at backstage.io/docs/deployment/docker.
#
# WHY `yarn build:all` AND NOT `yarn --cwd packages/backend build`. The upstream
# multi-stage example builds the backend only, and its own documentation says
# the resulting bundle does not contain the frontend. This app runs
# @backstage/plugin-app-backend (packages/backend/src/index.ts:13), which means
# the backend serves the UI and there is no separate frontend container. Build
# the backend alone and the image starts, answers /api/catalog, and serves a
# blank page. `build:all` is `backstage-cli repo build --all`, already declared
# in this repo's package.json.

# --- stage 1: the dependency skeleton -----------------------------------------
# Only package.json files, so a source edit does not invalidate `yarn install`.
FROM node:24-trixie-slim AS packages
WORKDIR /app
COPY backstage.json package.json yarn.lock ./
COPY .yarn ./.yarn
COPY .yarnrc.yml ./
COPY packages packages
COPY plugins plugins
RUN find packages \! -name "package.json" -mindepth 2 -maxdepth 2 -exec rm -rf {} \+

# --- stage 2: install and build -----------------------------------------------
FROM node:24-trixie-slim AS build
# better-sqlite3 is a native module and is compiled here, against this image's
# Node. It stays in the image because the scaffolder's dev config uses it; the
# container itself runs on Postgres (app-config.container.yaml).
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends libsqlite3-dev python3 build-essential && \
    rm -rf /var/lib/apt/lists/*
USER node
WORKDIR /app
COPY --from=packages --chown=node:node /app .
# NO NATIVE MODULE MAY FAIL TO BUILD AND STILL SHIP.
#
# Until 2026-08-25 this install ended `Done with warnings`, and the warning was
# `YN0009: keytar@npm:7.9.0 couldn't be built successfully (exit code 1)`. It was
# printed on every build for as long as this image has existed. Nobody acted on
# it, because acting on it took a dependency trace to find out whether it
# mattered -- so the finding was that it was harmless, and the next session paid
# for the same trace again. A warning that recurs and is always dismissed is not
# an instrument, it is a cost with a habit attached.
#
# It is closed at the source instead: root package.json declares
# `dependenciesMeta.keytar.built: false`, so yarn does not attempt the build and
# emits nothing. That leaves this grep with exactly one job -- catching the NEXT
# native module that fails, which today would have been lost in the noise of a
# warning everyone had learned to skip past.
#
# It also prints the failing module's own compiler output, not just the YN0009
# line. Yarn reports `logs can be found here: /tmp/xfs-.../build.log` -- a path
# inside a container that no longer exists by the time anyone reads the failure,
# so the one thing needed to act on it was the one thing thrown away. Three
# attempts to reproduce it outside the build failed on environment differences
# before this was added.
#
# `yarn install` exits 0 on YN0009, by design: a failed postinstall is not a
# failed resolution. So the exit status cannot be the gate and the log has to be.
# The log goes to a file rather than through `tee`, because RUN uses /bin/sh and
# the base image's sh is dash: PIPESTATUS is a bashism and $? after a pipe is
# tee's status, so a piped form would report success for a failed install.
RUN --mount=type=cache,target=/home/node/.cache/yarn,sharing=locked,uid=1000,gid=1000 \
    yarn install --immutable >/tmp/yarn.log 2>&1; s=$?; cat /tmp/yarn.log; [ "$s" -eq 0 ] || exit "$s"; \
    if grep -q 'YN0009' /tmp/yarn.log; then \
      echo "FATAL: a native module failed to build." >&2; \
      for f in /tmp/xfs-*/build.log; do \
        [ -f "$f" ] || continue; echo "--- $f ---" >&2; tail -40 "$f" >&2; \
      done; \
      exit 1; \
    fi
COPY --chown=node:node . .
RUN yarn tsc
RUN yarn build:all
RUN mkdir packages/backend/dist/skeleton packages/backend/dist/bundle \
    && tar xzf packages/backend/dist/skeleton.tar.gz -C packages/backend/dist/skeleton \
    && tar xzf packages/backend/dist/bundle.tar.gz -C packages/backend/dist/bundle

# --- stage 3: the production dependency tree ----------------------------------
# `yarn workspaces focus --all --production` does not just download packages, it
# compiles three of them from C++ source: better-sqlite3, cpu-features and
# keytar. Measured 2026-08-24, running it in the runtime image below: all three
# reported "couldn't be built successfully (exit code 1)" and the build failed
# after 12m39s, because that image carries libsqlite3-dev and no compiler -- the
# header with nothing to read it. Installing build-essential into the runtime
# image would fix the build by shipping a C++ toolchain to production, so the
# install happens in this stage and only its output crosses the line.
FROM node:24-trixie-slim AS deps
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends libsqlite3-dev python3 build-essential && \
    rm -rf /var/lib/apt/lists/*
USER node
WORKDIR /app
COPY --from=build --chown=node:node /app/.yarn ./.yarn
COPY --from=build --chown=node:node /app/.yarnrc.yml ./
COPY --from=build --chown=node:node /app/backstage.json ./
COPY --from=build --chown=node:node /app/yarn.lock /app/package.json /app/packages/backend/dist/skeleton/ ./
# The same gate, and this is the one that mattered. `--production` does not drop
# keytar: it arrives through @backstage/backend-defaults -> @backstage/cli-node,
# a real runtime dependency of packages/backend, not a dev one. Measured
# 2026-08-25 inside the shipped image: /app/node_modules/keytar is PRESENT and
# build/Release holds no .node binary at all. The catalogue serves 297 entities
# regardless, because nothing in the backend calls it -- but "ships a broken
# native module and gets away with it" is not a property to rely on quietly.
RUN --mount=type=cache,target=/home/node/.cache/yarn,sharing=locked,uid=1000,gid=1000 \
    yarn workspaces focus --all --production >/tmp/yarn.log 2>&1; s=$?; cat /tmp/yarn.log; [ "$s" -eq 0 ] || exit "$s"; \
    if grep -q 'YN0009' /tmp/yarn.log; then \
      echo "FATAL: a native module failed to build." >&2; \
      for f in /tmp/xfs-*/build.log; do \
        [ -f "$f" ] || continue; echo "--- $f ---" >&2; tail -40 "$f" >&2; \
      done; \
      exit 1; \
    fi; \
    rm -rf "$(yarn cache clean)"

# --- stage 4: the runtime image -----------------------------------------------
FROM node:24-trixie-slim
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*
# Least privilege. `node` is uid 1000 in this image and owns nothing it does not
# need; the catalogue file is mounted read-only from the host.
USER node
WORKDIR /app
# The whole of /app from deps: that stage's working directory holds exactly the
# backend skeleton and the node_modules built against it, which is what this
# stage used to produce for itself.
COPY --from=deps --chown=node:node /app ./
COPY --from=build --chown=node:node /app/packages/backend/dist/bundle/ ./
COPY --chown=node:node app-config*.yaml ./
# templates/ and examples/ are catalog locations, not decoration:
# templates/estate-component is the only scaffolder template the portal offers,
# and examples/org.yaml carries user:default/guest, which the guest auth
# provider resolves through the catalog. Drop it and sign-in breaks.
COPY --chown=node:node templates ./templates
COPY --chown=node:node examples ./examples
ENV NODE_ENV=production
CMD ["node", "packages/backend", "--config", "app-config.yaml", "--config", "app-config.container.yaml"]
