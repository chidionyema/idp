# idp#3448 CP0. A GPU pool for Ray/Unsloth training and vLLM/SGLang serving is outside the
# Always Free allowance; the Oracle compartment quota (bin/idp-oci-bootstrap) zeroes every
# compute family except A1, so no request for one can succeed. The Memgraph-vs-estate.db decision (does Memgraph become the new source of
# truth, or sit alongside catalog/estate.db) is the founder's call, recorded once.
@cp0
Feature: The graph-of-record decision is recorded

  Scenario: The Memgraph-vs-estate.db decision is recorded, not assumed
    Given idp#3448 is open
    When CP1 begins
    Then a comment on idp#3448 states whether Memgraph is the new source of truth (estate.db migrates in)
      or Memgraph sits alongside catalog/estate.db as a second store
    And no checkpoint after CP0 proceeds without that comment present
