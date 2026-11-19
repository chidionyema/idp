//! I-8096: Genesis split-authority certifier and EP-B reconciler.
//!
//! This crate exists so that `cage/i8096/src/certifier.rs` is a compiled, testable
//! artefact instead of an orphaned source file, and so the EP-B reconciler ships as
//! source on canonical main rather than as a couriered attachment.

pub mod accountability;
pub mod certifier;
pub mod reconciler_ep_b;

pub use reconciler_ep_b::{
    partition_into_lanes, resolve_7760_custody_route, Lane, PartitionReport, Subsystem,
    MAX_FILES_PER_LANE,
};
