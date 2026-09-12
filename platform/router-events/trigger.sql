-- THE TRIGGER. Every write to the router's lane table announces itself, at the moment it happens.
--
-- Founder 2026-09-12: "We rely on physics. Postgres instantly fires a NOTIFY." This is that line.
--
-- WHY A TRIGGER AND NOT A POLL. A poller has a window where the database and every reader
-- disagree, and the width of that window is the size of the lie. NOTIFY fires inside the writing
-- transaction, so the announcement and the change are one event.
--
-- payload carries only WHAT changed and WHICH row -- never a key, never a name. The reader asks
-- the source for the truth; the event says where to look. Notifications are visible to every
-- session on the database, so a payload with a credential in it would be a credential leak.
CREATE OR REPLACE FUNCTION estate_router_changed() RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify(
        'estate_router_changed',
        json_build_object(
            'op',        lower(TG_OP),
            'table',     TG_TABLE_NAME,
            'model',     COALESCE(NEW.model_name, OLD.model_name),
            'at',        to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
        )::text
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS router_lane_changed ON "LiteLLM_ProxyModelTable";
CREATE TRIGGER router_lane_changed
    AFTER INSERT OR UPDATE OR DELETE ON "LiteLLM_ProxyModelTable"
    FOR EACH ROW EXECUTE FUNCTION estate_router_changed();
