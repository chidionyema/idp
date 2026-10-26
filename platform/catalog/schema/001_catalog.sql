-- The catalog's schema, in the estate's one Postgres (D1: the record is Postgres;
-- catalog/estate.db is a generated cache of it, not a second source of truth).
--
-- These are the proposal's tables, in the proposal's names, because the proposal is
-- what the founder accepted. The names are unqualified inside a schema of the
-- catalog's own -- `catalog.nodes`, not `public.nodes` -- because the record lives
-- in the estate's shared `estate` database (the one CNPG cluster, one database per
-- consumer, and this one had been created, empty and owned, for exactly this), and
-- a table called `nodes` in a shared database is a collision waiting for the day
-- something else wants a table called `nodes`.
--
-- Every statement is IF NOT EXISTS, so the migration is idempotent: the census
-- applies it on every sweep, and applying it twice is a no-op rather than an error.
--
-- What each table is FOR, which is the part a schema does not say:
--
--   nodes        a thing that exists, with the plane that saw it, the state it is in
--                (managed / uncatalogued / live / disabled / blind), the moment it
--                was seen and the moment it goes stale. The expiry is not optional:
--                a node without one is a snapshot wearing a fact's name.
--   edges        topology: which thing calls, deploys, owns, guards or aliases which.
--   node_events  the state changes, so "it became uncatalogued" is a record and not
--                an inference from two snapshots.
--   facts        an attribute of one thing with its own TTL. A fact is not an edge.
--   aliases      the join. A canonical service carries the names the estate calls it
--                by -- the k8s id, the image, the label, the Backstage component --
--                so one thing is one node.
--   collectors   one row per collector, with when it last started, succeeded or
--                failed. A collector that dies is visible, not silent.
--   coverage     the completeness guarantee, one row per plane: the universe, how
--                much of it is classified, how much is uncatalogued with a reason,
--                and whether the plane was blind. BLIND is a row, never a zero.
--   drift        declared against live, with both values and when the mismatch was
--                first seen.
--   queries      the audit of what was asked and what came back. Digests only: no
--                arguments, no secrets.
--
-- The migration is applied by the census itself and, in the estate's native path, by
-- the CronJob in platform/catalog/ -- Flux applies that one. Two doors to the
-- same idempotent DDL is deliberate: the CronJob is how the schema arrives, and the
-- census's own apply is what makes a census against a fresh cluster work before
-- Flux has converged.
--
begin;

create schema if not exists catalog;

-- Everything below lands in the catalog's own schema, not in public. `set local`
-- so the choice ends with the transaction: the next thing that connects to this
-- database gets public again, and nothing else in the estate can see these tables
-- by accident.
set local search_path to catalog, public;

create table if not exists nodes (
  id          text primary key,
  type        text not null,
  name        text not null,
  plane       text not null,
  state       text not null,
  source      text not null,
  observed_at timestamptz not null,
  expires_at  timestamptz not null,
  confidence  real not null default 1.0,
  payload     jsonb not null default '{}'::jsonb
);
create index if not exists nodes_plane_idx on nodes (plane);
create index if not exists nodes_type_idx on nodes (type);
create index if not exists nodes_state_idx on nodes (state);

create table if not exists edges (
  src         text not null references nodes (id) on delete cascade,
  dst         text not null references nodes (id) on delete cascade,
  type        text not null,
  source      text not null,
  observed_at timestamptz not null,
  expires_at  timestamptz not null,
  confidence  real not null default 1.0,
  payload     jsonb not null default '{}'::jsonb,
  primary key (src, dst, type)
);
create index if not exists edges_src_idx on edges (src);
create index if not exists edges_dst_idx on edges (dst);

create table if not exists node_events (
  id         bigserial primary key,
  node_id    text not null,
  from_state text,
  to_state   text,
  at         timestamptz not null default now(),
  evidence   text
);
create index if not exists node_events_node_idx on node_events (node_id, at desc);

create table if not exists facts (
  id          text primary key,
  subject     text not null,
  predicate   text not null,
  object      text not null,
  source      text not null,
  observed_at timestamptz not null,
  expires_at  timestamptz not null,
  confidence  real not null default 1.0
);
create index if not exists facts_subject_idx on facts (subject);

create table if not exists aliases (
  alias      text not null,
  node_id    text not null references nodes (id) on delete cascade,
  source     text not null,
  confidence real not null default 1.0,
  primary key (alias, node_id)
);
create index if not exists aliases_node_idx on aliases (node_id);

create table if not exists collectors (
  name         text primary key,
  last_started timestamptz,
  last_success timestamptz,
  last_error   text,
  duration_ms  integer,
  counts       jsonb not null default '{}'::jsonb
);

create table if not exists coverage (
  plane        text primary key,
  universe     integer not null,
  classified   integer not null,
  uncatalogued integer not null,
  blind        integer not null,
  last_run     timestamptz,
  detail       jsonb not null default '{}'::jsonb
);

create table if not exists drift (
  service_id text not null,
  kind       text not null,
  declared   text,
  live       text,
  observed   text,
  first_seen timestamptz,
  last_seen  timestamptz,
  primary key (service_id, kind)
);

create table if not exists queries (
  id            bigserial primary key,
  at            timestamptz not null default now(),
  caller        text,
  tool          text,
  args_digest   text,
  result_digest text
);

-- The marker the migration writes, so "the schema is there" is a fact and not an
-- assumption. The copy Jobs in platform/estate-db/migrate use the same shape.
create table if not exists catalog_schema (
  applied_at timestamptz not null default now(),
  version    text not null
);

insert into catalog_schema (version)
select '001_catalog'
where not exists (select 1 from catalog_schema where version = '001_catalog');

commit;
