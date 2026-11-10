#!/usr/bin/env python3
"""Hosted eye-test: real signed local evidence, partition, revocation, restart and effect.

This is an isolated executable comparison, NOT production PEP enforcement.
It deliberately records a naive offline protected-effect counterexample.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def openssl(*args):
    return subprocess.run(["openssl", *args], check=True, capture_output=True)


class Device:
    def __init__(self, directory):
        self.dir = Path(directory)
        self.private = self.dir / "device-private.pem"
        self.public = self.dir / "device-public.pem"
        openssl("genpkey", "-algorithm", "Ed25519", "-out", str(self.private))
        openssl("pkey", "-in", str(self.private), "-pubout", "-out", str(self.public))
        self.id = hashlib.sha256(self.public.read_bytes()).hexdigest()[:16]

    def sign(self, data):
        msg, sig = self.dir / "message.bin", self.dir / "signature.bin"
        msg.write_bytes(data)
        openssl("pkeyutl", "-sign", "-inkey", str(self.private),
                "-rawin", "-in", str(msg), "-out", str(sig))
        return base64.b64encode(sig.read_bytes()).decode()

    def verify(self, data, signature):
        msg, sig = self.dir / "verify-message.bin", self.dir / "verify-signature.bin"
        msg.write_bytes(data)
        sig.write_bytes(base64.b64decode(signature))
        try:
            openssl("pkeyutl", "-verify", "-pubin", "-inkey", str(self.public),
                    "-rawin", "-in", str(msg), "-sigfile", str(sig))
            return True
        except subprocess.CalledProcessError:
            return False


def read_log(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def append(log, device, instruction, operation, epoch):
    previous = read_log(log)
    body = {
        "seq": len(previous) + 1,
        "prev": previous[-1]["digest"] if previous else "0" * 64,
        "device": device.id,
        "instruction_id": instruction,
        "operation": operation,
        "epoch": epoch,
        "kind": "proposed",
    }
    digest = hashlib.sha256(canonical(body)).hexdigest()
    envelope = {**body, "digest": digest}
    row = {**envelope, "signature": device.sign(canonical(envelope))}
    with log.open("a") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return row


def verify_log(rows, device):
    prev = "0" * 64
    for seq, row in enumerate(rows, 1):
        envelope = {k: v for k, v in row.items() if k != "signature"}
        payload = {k: v for k, v in envelope.items() if k != "digest"}
        if (row["seq"] != seq or row["prev"] != prev
                or row["digest"] != hashlib.sha256(canonical(payload)).hexdigest()
                or row["device"] != device.id
                or not device.verify(canonical(envelope), row["signature"])):
            return False
        prev = row["digest"]
    return True


class EffectBoundary:
    def __init__(self, path, epoch):
        self.path = Path(path)
        self.epoch = epoch
        self.seen = set()

    def apply(self, row, authorized_scope="probe-write"):
        if row["epoch"] != self.epoch or row["operation"] != authorized_scope:
            return "DENIED_STALE_OR_OUT_OF_SCOPE"
        if row["digest"] in self.seen:
            return "DEDUPLICATED"
        self.seen.add(row["digest"])
        with self.path.open("a") as handle:
            handle.write(row["digest"] + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return "EFFECT_WRITTEN"


def probe_url(url):
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "idp-eye-test/1"}),
            timeout=8,
        ) as response:
            sample = response.read(32768)
            result = {"status": response.status,
                      "latency_ms": round((time.perf_counter()-start)*1000, 1),
                      "content_type": response.headers.get("Content-Type", ""),
                      "body_sample_sha256": hashlib.sha256(sample).hexdigest()}
            # HTTP 200 can be an SPA fallback, not a functioning API.
            if "/api/" in url:
                try:
                    decoded = json.loads(sample)
                    result["valid_json"] = True
                    result["json_type"] = type(decoded).__name__
                    if isinstance(decoded, dict):
                        result["top_level_keys"] = sorted(decoded)[:30]
                        result["state_status"] = decoded.get("status")
                        for name in ("instructions", "yieldReceipts", "events"):
                            value = decoded.get(name)
                            if isinstance(value, list):
                                result[name + "_count"] = len(value)
                except (ValueError, UnicodeDecodeError):
                    result["valid_json"] = False
                    result["html_fallback_200"] = sample.lstrip().lower().startswith((b"<!doctype", b"<html"))
            return result
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "latency_ms": round((time.perf_counter()-start)*1000, 1)}
    except Exception as exc:
        return {"status": "UNREACHABLE", "exception": type(exc).__name__,
                "latency_ms": round((time.perf_counter()-start)*1000, 1)}


def main():
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="agent-prison-eye-") as d:
        home = Path(d)
        device = Device(home)
        log = home / "device-events.jsonl"
        effect = EffectBoundary(home / "protected-effects.log", epoch=1)
        signing_ms = []
        for i in range(12):
            t = time.perf_counter()
            row = append(log, device, "founder-eye-20261110", "probe-write", 1)
            signing_ms.append((time.perf_counter() - t) * 1000)
        first = effect.apply(row)
        # The founder revokes the grant while this replica has no connectivity.
        effect.epoch = 2
        # LOCAL-FIRST WITHOUT an authoritative current-epoch check is a counterexample:
        # an offline writer can still perform a local protected effect with stale authority.
        naive_offline_effect_path = home / "unsafe-local-effect"
        naive_offline_effect_path.write_text("unverified stale-epoch effect")
        # HYBRID: local-first evidence survives the crash, but protected effect is held.
        resumed = read_log(log)  # reopen durable disk after simulated agent loss
        verified = verify_log(resumed, device)
        rejected = effect.apply(resumed[-1]) if verified else "INVALID_SIGNATURE"
        # Re-authorize explicitly at the currently controlled boundary.
        fresh = append(log, device, "founder-eye-20261110", "probe-write", 2)
        accepted = effect.apply(fresh) if verify_log(read_log(log), device) else "INVALID_SIGNATURE"
        duplicate = effect.apply(fresh)
        with open(log, "r+") as file:
            tampered = file.read().replace("probe-write", "elevate-root", 1)
            file.seek(0)
            file.write(tampered)
            file.truncate()
        tamper_detected = not verify_log(read_log(log), device)
        effects = (home / "protected-effects.log").read_text().splitlines()
        result = {
            "kind": "ISOLATED_GITHUB_RUNNER_EYE_TEST_NOT_ESTATE_DEPLOYMENT",
            "comparison": {
                "central_online": {"first_effect": first, "post_revoke_effect": rejected,
                                   "offline_availability": "NONE"},
                "naive_local_first": {"offline_evidence_survives": len(resumed) == 12,
                                      "stale_protected_local_effect": naive_offline_effect_path.exists(),
                                      "verdict": "UNSAFE_FOR_REVOCABLE_PROTECTED_LOCAL_EFFECTS"},
                "hybrid": {"signed_chain_verified": verified, "stale_replay": rejected,
                           "fresh_epoch": accepted, "duplicate": duplicate,
                           "tampering_detected": tamper_detected,
                           "protected_effect_count": len(effects)},
            },
            "measurements": {"signed_durable_append_p50_ms": round(statistics.median(signing_ms), 2),
                             "signed_durable_append_p95_ms": round(sorted(signing_ms)[-1], 2),
                             "elapsed_ms": round((time.perf_counter()-started)*1000, 1)},
            "estate_operational_verified": False,
        }
    # The only remote probes are GETs; no production side effects or privileged credentials.
    result["live_founder_surface"] = {
        "page": probe_url("https://genesis-founder-surface.pages.dev/"),
        "brain_state_api": probe_url("https://genesis-founder-surface.pages.dev/api/brain/state"),
    }
    registry = json.loads(Path("catalog/dof-registry.json").read_text())
    result["estate_source_control_mode"] = registry["control"]["mode"]
    errors = []
    c = result["comparison"]
    if c["hybrid"] != {
        "signed_chain_verified": True, "stale_replay": "DENIED_STALE_OR_OUT_OF_SCOPE",
        "fresh_epoch": "EFFECT_WRITTEN", "duplicate": "DEDUPLICATED",
        "tampering_detected": True, "protected_effect_count": 2
    }:
        errors.append("HYBRID_EYE_TEST_FAILED")
    if not c["naive_local_first"]["stale_protected_local_effect"]:
        errors.append("OFFLINE_COUNTEREXAMPLE_NOT_EXERCISED")
    result["experiment_errors"] = errors
    Path("agent-prison-eye.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as fh:
            fh.write("## Real GitHub-hosted agent-prison eye test\n\n")
            fh.write("| Observable | Result |\n|---|---|\n")
            for name, value in c["hybrid"].items():
                fh.write(f"| Hybrid {name} | {value} |\n")
            fh.write(f"| Source DoF control | {result['estate_source_control_mode']} |\n")
            fh.write(f"| Founder page HTTP | {result['live_founder_surface']['page']['status']} |\n")
            fh.write(f"| Founder brain API HTTP | {result['live_founder_surface']['brain_state_api']['status']} |\n")
            fh.write("| Production estate PEP certified | **NO — this is a hosted isolated canary** |\n")
    if errors:
        raise SystemExit("; ".join(errors))


if __name__ == "__main__":
    main()
