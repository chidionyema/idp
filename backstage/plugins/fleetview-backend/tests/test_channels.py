from fleetview_backend import channels


def test_lists_every_manifest_and_skips_malformed(tmp_path, monkeypatch):
    for name in ("a", "b"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "channel.yaml").write_text(
            f"id: {name}\nsubject: estate.channel.{name}\nhow_it_works: x\nvisual: {{scene: vault}}\n"
        )
    (tmp_path / "bad").mkdir()
    (tmp_path / "bad" / "channel.yaml").write_text("id: [unclosed")
    monkeypatch.setenv("FLEETVIEW_PLATFORM_DIR", str(tmp_path))
    body, status = channels.list_channels()
    assert status == 200 and body["count"] == 2
    assert [c["id"] for c in body["channels"]] == ["a", "b"]


def test_real_repo_serves_a_channel_for_every_component(monkeypatch):
    monkeypatch.delenv("FLEETVIEW_PLATFORM_DIR", raising=False)
    body, _ = channels.list_channels()
    dirs = [
        p
        for p in channels._platform_dir().iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ]
    assert body["count"] == len(dirs)
