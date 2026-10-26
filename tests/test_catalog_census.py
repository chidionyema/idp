"""The census's contract, measured rather than asserted.

Every test here states a property the catalog has to keep, and each one can fail:
the coverage invariant (classified + uncatalogued = universe), the blindness
semantics (a plane that could not be read says so, it does not report zero), the
join rules and their order, the ambiguity rule, and the write path's quoting.

The collectors are exercised against fixtures, never against the founder's
machine: a test that reads the real cluster is a test that fails when the estate
is busy, and a test that reads the real disk is a test that reads the founder's
disk without asking.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from catalog.census.census import build_coverage, run_census, validate  # noqa: E402
from catalog.census.join import (  # noqa: E402
    JoinContext,
    RepoInfo,
    image_repo_name,
    image_repository_name,
    join,
    normalize_image,
)
from catalog.census.model import (  # noqa: E402
    PLANE_GIT,
    PLANE_HOST,
    PLANE_K8S,
    REASON_NO_OWNER,
    REASON_NO_REPO,
    RULE_IMAGE_REPO,
    RULE_K8S_LABEL,
    RULE_OTEL_NAME,
    STATE_MANAGED,
    STATE_UNCATALOGUED,
    Observation,
    merge_observations,
    service_id,
    ttl_expiry,
)
from catalog.census.planes import CollectorConfig, _dockerfile_images, _repo_for_path  # noqa: E402
from catalog.census.store import Record, _sql_json, _sql_literal  # noqa: E402


def _observation(**kwargs) -> Observation:
    base = {
        "id": "k8s:deployment:estate/router",
        "type": "workload",
        "name": "router",
        "plane": PLANE_K8S,
        "source": "test",
        "observed_at": "2026-10-26T00:00:00Z",
        "expires_at": "2026-10-26T00:03:00Z",
    }
    base.update(kwargs)
    return Observation(**base)


def _context(**kwargs) -> JoinContext:
    ctx = JoinContext()
    ctx.repos["idp"] = RepoInfo(
        id="git:repo:chidionyema/idp",
        org="chidionyema",
        name="idp",
        owner="chidionyema",
    )
    ctx.repos["estate-scheduler"] = RepoInfo(
        id="git:repo:chidionyema/estate-scheduler",
        org="chidionyema",
        name="estate-scheduler",
        owner="chidionyema",
    )
    for key, value in kwargs.items():
        setattr(ctx, key, value)
    return ctx


# --- the join rules ------------------------------------------------------------


def test_rule_2_the_k8s_name_label_wins():
    obs = _observation(
        payload={
            "labels": {"app.kubernetes.io/name": "router"},
            "image": "ghcr.io/chidionyema/idp/router",
        }
    )
    outcome = join(obs, _context())
    assert outcome.alias == "router"
    assert outcome.rule == RULE_K8S_LABEL
    assert not outcome.ambiguous


def test_rule_4_the_image_names_the_service_when_nothing_else_does():
    obs = _observation(payload={"image": "ghcr.io/chidionyema/idp/router"})
    outcome = join(obs, _context())
    assert outcome.alias == "router"
    assert outcome.rule == RULE_IMAGE_REPO


def test_rule_3_the_telemetry_name_is_an_identity():
    obs = _observation(
        payload={
            "otel_service_name": "router",
            "image": "ghcr.io/chidionyema/idp/router",
        }
    )
    outcome = join(obs, _context())
    assert outcome.alias == "router"
    assert outcome.rule == RULE_OTEL_NAME


def test_two_service_names_that_disagree_are_ambiguous_and_are_not_guessed():
    obs = _observation(
        payload={
            "labels": {"app.kubernetes.io/name": "estate-mcp"},
            "otel_service_name": "mcp-estate-refresh",
        }
    )
    outcome = join(obs, _context())
    assert outcome.ambiguous is True
    assert {c.alias for c in outcome.candidates} == {"estate-mcp", "mcp-estate-refresh"}


def test_names_that_are_one_thing_at_two_depths_are_not_ambiguous():
    obs = _observation(
        payload={
            "labels": {"app.kubernetes.io/name": "cert-manager"},
            "image": "quay.io/jetstack/cert-manager-controller:v1.21.1",
        }
    )
    outcome = join(obs, _context())
    assert outcome.ambiguous is False
    assert outcome.alias == "cert-manager"


def test_the_image_name_does_not_outrank_the_label_the_estate_gave():
    # The estate's idp repository builds an image called estate-scheduler and the
    # service that runs it is called dagster. The label is the service.
    obs = _observation(
        payload={
            "labels": {"app.kubernetes.io/name": "dagster"},
            "image": "ghcr.io/chidionyema/estate-scheduler",
        }
    )
    outcome = join(obs, _context())
    assert outcome.alias == "dagster"
    assert outcome.ambiguous is False


def test_the_repo_behind_an_image_is_found_through_the_repo_that_builds_it():
    ctx = _context()
    ctx.images["ghcr.io/chidionyema/estate-scheduler"] = "idp"
    obs = _observation(
        payload={
            "labels": {"app.kubernetes.io/name": "dagster"},
            "image": "ghcr.io/chidionyema/estate-scheduler",
        }
    )
    outcome = join(obs, ctx)
    assert outcome.repo is not None
    assert outcome.repo.name == "idp"
    assert outcome.owner == "chidionyema"


def test_a_manual_override_wins_over_every_rule_and_says_so():
    ctx = _context(overrides={"router": "estate-router"})
    obs = _observation(payload={"labels": {"app.kubernetes.io/name": "router"}})
    outcome = join(obs, ctx)
    assert outcome.alias == "estate-router"
    assert not outcome.ambiguous


def test_the_launchd_label_names_the_service_on_the_host_plane():
    obs = _observation(
        id="launchd:ai.estate.cockpit",
        type="job",
        name="ai.estate.cockpit",
        plane=PLANE_HOST,
        payload={"label": "ai.estate.cockpit", "repo": "idp"},
    )
    outcome = join(obs, _context())
    assert outcome.alias == "cockpit"


# --- the image name grammar ----------------------------------------------------


@pytest.mark.parametrize(
    "image,service,repo",
    [
        ("ghcr.io/chidionyema/idp/router", "router", "idp"),
        (
            "ghcr.io/chidionyema/estate-scheduler",
            "estate-scheduler",
            "estate-scheduler",
        ),
        ("ghcr.io/chidionyema/mirror/external-dns", "external-dns", "mirror"),
        ("docker.io/library/nginx:1.27", "nginx", "nginx"),
        ("quay.io/calico/node:v3.32.2", "node", "node"),
        ("ghcr.io/chidionyema/backstage:main-14830-abc", "backstage", "backstage"),
        ("ghcr.io/chidionyema/backstage@sha256:deadbeef", "backstage", "backstage"),
    ],
)
def test_the_image_name_grammar(image, service, repo):
    assert image_repository_name(image) == service
    assert image_repo_name(image) == repo


def test_normalize_image_drops_the_tag_and_the_digest():
    assert (
        normalize_image("ghcr.io/chidionyema/backstage:main-1")
        == "ghcr.io/chidionyema/backstage"
    )
    assert (
        normalize_image("ghcr.io/chidionyema/backstage@sha256:abc")
        == "ghcr.io/chidionyema/backstage"
    )


# --- the coverage invariant ----------------------------------------------------


def _fake_census() -> list[Observation]:
    """Three objects, three outcomes, and one plane that could not be read."""

    return [
        _observation(
            id="a",
            name="a",
            state=STATE_MANAGED,
            payload={"labels": {"app.kubernetes.io/name": "a"}},
        ),
        _observation(
            id="b",
            name="b",
            state=STATE_UNCATALOGUED,
            reason=REASON_NO_REPO,
            payload={},
        ),
        _observation(
            id="c",
            name="c",
            state=STATE_UNCATALOGUED,
            reason=REASON_NO_OWNER,
            payload={},
        ),
    ]


def test_classified_plus_uncatalogued_equals_the_universe():
    from catalog.census.census import Census
    from catalog.census.model import PlaneResult

    census = Census(started_at="2026-10-26T00:00:00Z")
    census.observations = {obs.id: obs for obs in _fake_census()}
    census.results.append(PlaneResult(plane=PLANE_K8S, collector="census-k8s"))
    rows = build_coverage(census)
    k8s = next(row for row in rows if row["plane"] == PLANE_K8S)
    assert k8s["universe"] == 3
    assert k8s["classified"] + k8s["uncatalogued"] == k8s["universe"]


def test_a_plane_that_could_not_be_read_is_blind_and_never_a_zero():
    from catalog.census.census import Census
    from catalog.census.model import PlaneResult

    census = Census(started_at="2026-10-26T00:00:00Z")
    census.results.append(
        PlaneResult(
            plane=PLANE_GIT,
            collector="census-git",
            blind=True,
            blind_reason="gh timed out",
        )
    )
    rows = build_coverage(census)
    git = next(row for row in rows if row["plane"] == PLANE_GIT)
    assert git["blind"] == 1
    assert "timed out" in git["detail"]["blind_reason"]


def test_every_reason_is_from_the_closed_set():
    from catalog.census.model import UNCATALOGUED_REASONS

    for obs in _fake_census():
        if obs.state == STATE_UNCATALOGUED:
            assert obs.reason in UNCATALOGUED_REASONS


# --- the collectors, against fixtures ------------------------------------------


def test_the_images_a_repository_builds_are_read_from_its_dockerfiles(tmp_path):
    (tmp_path / "estate-scheduler.Dockerfile").write_text(
        "FROM scratch\n", encoding="utf-8"
    )
    (tmp_path / "platform" / "voice-router").mkdir(parents=True)
    (tmp_path / "platform" / "voice-router" / "Dockerfile").write_text(
        "FROM scratch\n", encoding="utf-8"
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "Dockerfile").write_text(
        "FROM scratch\n", encoding="utf-8"
    )
    images = _dockerfile_images(str(tmp_path), "chidionyema")
    assert "ghcr.io/chidionyema/estate-scheduler" in images
    assert "ghcr.io/chidionyema/voice-router" in images
    assert not any("node_modules" in image for image in images)


def test_the_repository_behind_a_program_is_found_by_looking(tmp_path):
    repo = tmp_path / "idp"
    (repo / ".git").mkdir(parents=True)
    (repo / "bin").mkdir()
    program = str(repo / "bin" / "sb")
    cfg = CollectorConfig(code_root=str(tmp_path))
    assert _repo_for_path(cfg, program) == "idp"


def test_a_program_outside_the_code_root_has_no_repository(tmp_path):
    cfg = CollectorConfig(code_root=str(tmp_path))
    assert _repo_for_path(cfg, "/usr/local/bin/python3") == ""


# --- the write path ------------------------------------------------------------


def test_a_value_with_a_quote_cannot_break_out_of_its_literal():
    literal = _sql_literal("router'; drop table nodes; --")
    assert literal == "'router''; drop table nodes; --'"
    assert literal.count("'") % 2 == 0


def test_json_is_quoted_as_a_json_literal():
    assert _sql_json({"a": 1}) == "'{\"a\":1}'::jsonb"


def test_the_census_refuses_to_write_an_alias_that_points_at_nowhere():
    """The failure the foreign key would catch at the far end of a long write."""
    from catalog.census.census import Census

    census = Census(started_at="2026-10-26T00:00:00Z")
    census.observations = {"a": _observation(id="a")}
    census.aliases.append(("a", "svc:nothing", "census-join:rule-2-label", 0.9))
    with pytest.raises(ValueError) as raised:
        validate(census)
    assert "svc:nothing" in str(raised.value)


def test_a_census_that_walked_nothing_reports_nothing_and_blinds_every_plane():
    census = run_census(planes=[], cfg=CollectorConfig())
    assert census.observations == {}
    assert len(census.coverage) == 4
    assert all(row["blind"] == 1 for row in census.coverage)
    assert all(row["universe"] == 0 for row in census.coverage)


# --- the freshness contract ----------------------------------------------------


def test_every_observation_carries_an_expiry():
    expiry = ttl_expiry(180)
    obs = _observation(expires_at=expiry)
    assert obs.expires_at.endswith("Z")
    assert obs.expires_at > obs.observed_at


def test_two_planes_that_see_one_thing_produce_one_row():
    first = _observation(id="x", observed_at="2026-10-26T00:00:00Z")
    second = _observation(id="x", observed_at="2026-10-26T00:01:00Z")
    merged = merge_observations([first, second])
    assert len(merged) == 1
    assert merged["x"].observed_at == "2026-10-26T00:01:00Z"


def test_the_service_id_is_the_proposal_s_grammar():
    assert service_id("router") == "svc:router"


def test_the_record_will_not_create_a_second_database():
    """The record is the estate database; a second one is the failure D1 forbids."""

    class _FakeRecord(Record):
        """A record with no cluster: every statement is refused before it runs."""

        def query(self, sql, database=None):
            self.statements = getattr(self, "statements", [])
            self.statements.append(sql)
            return []

        def psql(
            self, sql, database=None, tuples=False
        ):  # pragma: no cover - must not be called
            raise AssertionError("the record tried to run SQL against the cluster")

    record = _FakeRecord(database="catalog-that-does-not-exist")
    with pytest.raises(Exception) as raised:
        record.ensure_database()
    message = str(raised.value)
    assert "catalog-that-does-not-exist" in message
    assert "does not create a second database" in message
    assert record.statements == [
        "select 1 from pg_database where datname = 'catalog-that-does-not-exist'"
    ]
