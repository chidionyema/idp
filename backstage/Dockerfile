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
RUN --mount=type=cache,target=/home/node/.cache/yarn,sharing=locked,uid=1000,gid=1000 \
    yarn install --immutable
COPY --chown=node:node . .
RUN yarn tsc
RUN yarn build:all
RUN mkdir packages/backend/dist/skeleton packages/backend/dist/bundle \
    && tar xzf packages/backend/dist/skeleton.tar.gz -C packages/backend/dist/skeleton \
    && tar xzf packages/backend/dist/bundle.tar.gz -C packages/backend/dist/bundle

# --- stage 3: the runtime image -----------------------------------------------
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
COPY --from=build --chown=node:node /app/.yarn ./.yarn
COPY --from=build --chown=node:node /app/.yarnrc.yml ./
COPY --from=build --chown=node:node /app/backstage.json ./
COPY --from=build --chown=node:node /app/yarn.lock /app/package.json /app/packages/backend/dist/skeleton/ ./
RUN --mount=type=cache,target=/home/node/.cache/yarn,sharing=locked,uid=1000,gid=1000 \
    yarn workspaces focus --all --production && rm -rf "$(yarn cache clean)"
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
