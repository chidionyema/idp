//! penny-core: the token-efficiency engine behind pennyd.
//!
//! Layers (cheapest first, per the cascade doctrine):
//!   1. exact cache      — don't pay for the same request twice
//!   2. shaping          — provider-side cache headers, output caps, tool truncation
//!   3. routing          — cheap-first lane cascade with circuit breakers
//!   4. budgets          — hard per-key daily ceilings; refuse, never silently degrade
//!   5. decision log     — hash-chained, replayable record of every decision
pub mod anthropic;
pub mod budget;
pub mod cache;
pub mod config;
pub mod decision_log;
pub mod dialect;
pub mod error;
pub mod keys;
pub mod ledger;
pub mod providers;
pub mod router;
pub mod shaping;
