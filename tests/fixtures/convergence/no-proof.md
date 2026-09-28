Fix the odd spike where the edge router wedged under the load test

The edge was holding a stale idle timeout against a long-lived stream and
reconnecting the whole mesh every time one leg went quiet. Bump the idle time
out up to the stream's own keepalive so a pause does not read as a drop, and
let the mesh re-run only on a real send failure.

No vcluster was used to prove this change. It is a config text change reviewed
by eye. It is being merged on the strength of two fixtures and a code review,
which is exactly the class this gate exists to refuse: a change that reached
no shadow dimension is unproven, however obviously safe it looks.
