import asyncio
import os
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from security_core import MAPLEGuard

# LAW 4: secrets by name only, from the vault. No literal password in source.
DATABASE_URL = os.environ["DATABASE_URL"]
CURATION_LOCK_ID = 883921  # Unique Advisory Lock Int for Curation Daemon

async def run_curation_tick(conn):
    """Evaluates unpromoted private memories for shared elevation or quarantine."""
    async with conn.cursor() as cur:
        # Sweep unpromoted memories
        await cur.execute(
            """
            SELECT id, relevance_rho, truthfulness_tau, harm_h, taint_level
            FROM memories
            WHERE is_shared = FALSE AND is_quarantined = FALSE
            LIMIT 50;
            """
        )
        unpromoted = await cur.fetchall()

        for m in unpromoted:
            should_promote = MAPLEGuard.evaluate_promotion_gate(
                rho=m["relevance_rho"],
                tau=m["truthfulness_tau"],
                h=m["harm_h"]
            )
            if should_promote:
                await cur.execute("UPDATE memories SET is_shared = TRUE WHERE id = %s;", (m["id"],))
            elif m["harm_h"] > 0.40 or m["taint_level"] > 0.70:
                # Quarantine harmful or highly tainted memories
                await cur.execute("UPDATE memories SET is_quarantined = TRUE WHERE id = %s;", (m["id"],))

async def main():
    pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        min_size=1,
        max_size=2,
        check=AsyncConnectionPool.check_connection,
        kwargs={"autocommit": True, "row_factory": dict_row}
    )
    await pool.open()
    print("CURATION_DAEMON: Active. Entering leader election loop...")

    while True:
        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    # Transaction-scoped advisory lock prevents pool-backend deadlocks
                    await cur.execute("SELECT pg_try_advisory_xact_lock(%s);", (CURATION_LOCK_ID,))
                    is_leader = (await cur.fetchone())["pg_try_advisory_xact_lock"]

                    if is_leader:
                        await run_curation_tick(conn)
                        await asyncio.sleep(10)
                    else:
                        # Follower pod: yield leadership loop
                        await asyncio.sleep(30)
        except Exception as e:
            print(f"Curation Loop Fault: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
