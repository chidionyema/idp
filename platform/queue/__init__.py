"""The estate's task queue.

platform/ has no __init__.py (idp#3564): it collides with the stdlib `platform` module the
moment anything imports it bare, and pytest imports `platform` at startup. So this package
cannot be reached by its dotted name from a process that has the stdlib module loaded:
`from platform.queue import dispatcher` raises ModuleNotFoundError ("'platform' is not a
package"). Every caller in the execution substrate hit that, and the worker pool died on
it before it claimed a task.

`load_dispatcher()` loads the dispatcher by file path and seeds sys.modules under its real
dotted name. That is the pattern the estate already uses for platform.eval
(tests/pareval/test_policy_validation.py), and it lives here so there is ONE loader for
the queue rather than one per caller.
"""

import importlib.util
import os
import sys


def load_dispatcher():
    """The queue dispatcher, loaded and seeded under its real dotted name.

    Returns the dispatcher module. Calling it twice returns the same module.
    """
    if "platform.queue.dispatcher" in sys.modules:
        return sys.modules["platform.queue.dispatcher"]

    here = os.path.dirname(os.path.abspath(__file__))
    for dotted, path in (
        ("platform.queue", os.path.join(here, "__init__.py")),
        ("platform.queue.dispatcher", os.path.join(here, "dispatcher.py")),
    ):
        if dotted in sys.modules:
            continue
        spec = importlib.util.spec_from_file_location(dotted, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[dotted] = module
        spec.loader.exec_module(module)

    package = sys.modules.get("platform.queue")
    dispatcher = sys.modules["platform.queue.dispatcher"]
    if package is not None:
        # so a later `from platform.queue import dispatcher` finds it
        package.dispatcher = dispatcher
    return dispatcher
