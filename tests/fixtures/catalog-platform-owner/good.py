# must_pass fixture for rules.yaml's catalog-platform-owner rule: every row carries a real owner.
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
        "group:default/platform",
    ),
}
