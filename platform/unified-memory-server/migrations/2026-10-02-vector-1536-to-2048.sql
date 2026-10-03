-- 2026-10-02: move the estate's memory vectors from 1536 to 2048 dims.
--
-- WHY: every hop of the 1536 embed chain is dry at the vendor (openrouter 402
-- zero credit, gemini 402 prepaid depleted, cohere trial). The one free lane we
-- own -- nvidia/nemotron-3-embed-1b, on the router's 10,000-requests/day/model
-- meter -- emits 2048 and refuses truncation ("dimensions must be one of 2048").
-- Founder chose the free lane over funding a vendor: the column follows the lane.
--
-- SAFE PATTERN, and it is not optional on a live store: add a nullable 2048
-- column, leave the 1536 one in place, swap only after a backfill has filled the
-- new one. A single ALTER ... TYPE vector(2048) against 1152 existing 1536
-- vectors either errors or silently mis-shapes them, and both are worse than the
-- dark-embedding state we are fixing. Old vectors are NOT convertible: a 1536
-- vector is not a prefix of its 2048 counterpart, it is a different embedding
-- space entirely. Every stored vector must be re-embedded, which is why this
-- migration is paired with the backfill task and not run alone.
--
-- Run inside a transaction: a failure mid-way leaves the old column intact.

BEGIN;

-- otto_facts (otto_gateway): 1211 facts, 1152 embedded at 1536.
ALTER TABLE otto_facts
    ADD COLUMN IF NOT EXISTS embedding_2048 vector(2048);

-- memories (memory): 47 facts, 0 embedded -- so nothing to re-embed here, the
-- new column becomes the only one at swap time and the backfill fills it.
ALTER TABLE memories
    ADD COLUMN IF NOT EXISTS embedding_2048 vector(2048);

COMMIT;

-- The swap (indexes + rename + drop) is deliberately NOT in this file: it must
-- run only after the backfill has populated embedding_2048 for every row, so it
-- is a second, separate step taken by hand once this count reads done = total
-- for BOTH tables (1211 in otto_facts, 47 in memories -- rerun the query per
-- database, they are not in the same one):
--
--   SELECT count(*) FILTER (WHERE embedding_2048 IS NOT NULL) AS done,
--          count(*)                        AS total
--   FROM otto_facts;   -- then: FROM memories, on database `memory`
--
-- The backfill re-embeds each row through the `embed-free` lane and writes the
-- result into embedding_2048. It is a one-paste UPDATE, not a service: at this
-- size (1211 + 47 rows) it is seconds of work, and a script with its own
-- progress reporting and CI rung would be more apparatus than the data warrants.
--
-- Then the swap, one transaction per store:
--
--   BEGIN;
--   DROP INDEX IF EXISTS idx_<table>_embedding_hnsw;
--   ALTER TABLE <table> DROP COLUMN IF EXISTS embedding;
--   ALTER TABLE <table> RENAME COLUMN embedding_2048 TO embedding;
--   CREATE INDEX IF NOT EXISTS idx_<table>_embedding_hnsw
--     ON <table> USING hnsw (embedding vector_cosine_ops);
--   COMMIT;
--
-- Doing the rename before every row is re-embedded strands the unre-embedded
-- rows in a space nothing searches, silently -- the same write-only failure this
-- whole change exists to end. That is why the count above is the gate.
