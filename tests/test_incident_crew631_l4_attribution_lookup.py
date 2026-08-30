"""crew#631: an L4 FAIL is attributed, never re-narrated. The prover reads a prior run's trace
id again on request (IDP_PROVE_LOOKUP_TRACE) and prints an info line, not an assertion."""

import pathlib
import re

IDP = pathlib.Path(__file__).resolve().parents[1]


def test_the_lookup_is_wired_from_dispatch_input_to_the_prover_and_is_not_graded():
    wf = (IDP / ".github/workflows/verdict-langfuse.yml").read_text()
    assert (
        "lookup_trace:" in wf
        and "IDP_PROVE_LOOKUP_TRACE: ${{ inputs.lookup_trace }}" in wf
    )
    prove = (IDP / "bin/idp-prove").read_text()
    block = prove[prove.index("IDP_PROVE_LOOKUP_TRACE") :]
    assert re.search(r'print\(f"info\s+prove\s+l4\.attribution\.prior_trace_', block)
    assert "assertions +=" not in block.split("    else:")[0]
