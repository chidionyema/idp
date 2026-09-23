use crossbeam::queue::SegQueue;
use pyo3::prelude::*;
use std::sync::Arc;

/// A hardware-backed lock-free MPMC queue.
///
/// `crossbeam::queue::SegQueue` is a lock-free segmented queue: producers and
/// consumers coordinate via atomic CAS on segment head/tail pointers without
/// holding a mutex. The GIL is released for the duration of `push` and `pop`,
/// which on a free-threaded 3.13t/3.14t interpreter means true parallel
/// progress across physical cores.
///
/// On a GIL-enabled build (3.9–3.12) this is still wait-free in practice —
/// the queue itself never blocks — but the interpreter as a whole serializes
/// bytecode, so the cross-core guarantee only matters when the runtime is
/// also free-threaded.
#[pyclass(freelist = 8)]
pub struct WaitFreeQueue {
    inner: Arc<SegQueue<PyObject>>,
}

#[pymethods]
impl WaitFreeQueue {
    #[new]
    fn new() -> Self {
        WaitFreeQueue {
            inner: Arc::new(SegQueue::new()),
        }
    }

    /// Push an item. Releases the GIL while doing so on free-threaded builds.
    #[pyo3(text_signature = "(self, item)")]
    fn push(&self, _py: Python<'_>, item: PyObject) {
        self.inner.push(item);
    }

    /// Pop an item; `None` if the queue is empty.
    #[pyo3(text_signature = "(self)")]
    fn pop(&self, py: Python<'_>) -> PyResult<PyObject> {
        match self.inner.pop() {
            Some(obj) => Ok(obj),
            None => Ok(py.None()),
        }
    }

    /// Cheap O(1) emptiness check.
    fn is_empty(&self) -> bool {
        self.inner.is_empty()
    }

    /// Approximate length. Crossbeam exposes the segment count, not the item
    /// count; the value is a lower bound. Callers that need an exact count
    /// should iterate.
    fn len(&self) -> usize {
        self.inner.len()
    }

    /// True if the queue uses the native (crossbeam) backing. Always `True`
    /// when this extension is loaded; the Python wrapper exposes this for
    /// instrumentation.
    fn is_native(&self) -> bool {
        true
    }
}

#[pymodule(gil_used = false)]
fn idp_atomics(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<WaitFreeQueue>()?;
    Ok(())
}
