# idp#3448 CP0. estate-defaults.yaml caps node_pool.budget_monthly_usd at 50 total; a GPU
# pool for Ray/Unsloth training and vLLM/SGLang serving is paid capacity above that cap, so
# it is FOUNDER ACTION under capacity-requests-need-proof and LAW 47, never a silent
# assumption. The Memgraph-vs-estate.db decision (does Memgraph become the new source of
# truth, or sit alongside catalog/estate.db) is the founder's call, recorded once.
@cp0
Feature: GPU capacity is a named FOUNDER ACTION, and the graph-of-record decision is recorded

  Scenario: A GPU node pool request above the budget cap is refused without founder sign-off
    Given estate-defaults.yaml node_pool.budget_monthly_usd is 50
    And a capacity request for a GPU node pool priced above that cap
    When the capacity-requests-need-proof admission policy evaluates the request
    Then the request is refused
    And idp#3448 carries a FOUNDER ACTION line naming the exact monthly figure and the node shape

  Scenario: The Memgraph-vs-estate.db decision is recorded, not assumed
    Given idp#3448 is open
    When CP1 begins
    Then a comment on idp#3448 states whether Memgraph is the new source of truth (estate.db migrates in)
      or Memgraph sits alongside catalog/estate.db as a second store
    And no checkpoint after CP0 proceeds without that comment present
