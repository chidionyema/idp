# must_fail fixture for rules.yaml's catalog-platform-owner rule: one row's owner (4th field)
# is empty, the exact shape every LAYERS row was in before bin/catalog-platform's owner guard.
LAYERS = {
    "edge": (
        "edge",
        "Edge",
        "How traffic gets in.",
        "group:default/platform",
    ),
    "dns": (
        "edge",
        "DNS",
        "Every hostname the estate answers to.",
        "",
    ),
}
