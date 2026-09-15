"""GOV-01 (idp#3525 CP8, spec section 6): "dependency scan of the routing path shows zero
laptop-resolved targets. Dev-local convenience files not in the routing path are exempt by
classification record." METHOD: config audit.

This proves both halves: the routing path itself is clean, and the exemption list is a real
classification record naming files the scanner can still see the pattern in -- not files it
was simply never pointed at.
"""

from __future__ import annotations

from sovereign.engine import routing_path_audit as audit


def test_the_production_routing_path_has_zero_laptop_resolved_targets() -> None:
    """GOV-01's own ACCEPT line: platform/llm/**/*.yaml, the cluster-deployed lane, must
    show zero laptop-resolved targets."""
    assert audit.scan_routing_path() == {}


def test_every_exempt_file_is_a_real_classification_record_not_an_unscanned_blind_spot() -> (
    None
):
    """Each EXEMPT_FILES entry carries a reason, and the scanner still finds the very
    pattern it is exempting -- proving the exemption is a recorded decision about a file
    the scanner saw, not silence about a file it never looked at."""
    assert audit.EXEMPT_FILES, "no classification record exists"
    for path, reason in audit.EXEMPT_FILES.items():
        assert reason.strip(), f"{path}: exempt with no reason on record"
    hits = audit.scan_exempt_files()
    assert set(hits) == set(audit.EXEMPT_FILES), (
        "exempt files no longer contain the laptop pattern they were exempted for; "
        "drop them from EXEMPT_FILES"
    )


def test_exempt_files_are_outside_the_routing_path_directories() -> None:
    """A file cannot be both scanned-as-routing-path and exempt -- that would be the
    scanner clearing a target GOV-01 requires it to catch."""
    for path in audit.EXEMPT_FILES:
        assert not path.startswith("platform/llm/"), (
            f"{path} is inside the routing path and cannot be exempt"
        )
