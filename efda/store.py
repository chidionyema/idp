"""The artifact and checkpoint store.

The address is deterministic: an artifact is not found by searching, it is
handed over.

    {cluster}/{namespace}/{component_class}/{runner_id}/artifact.json

The store speaks RESP to Redis over a plain socket (no client library, no
dependency), and every write is mirrored into a bounded local write-ahead log
so that a kill at the wrong moment cannot lose the evidence: the WAL drains
the moment the sink is reachable again.
"""

from __future__ import annotations

import json
import os
import socket
import time

from .contract import artifact_address

DEFAULT_REDIS_HOST = "127.0.0.1"
DEFAULT_REDIS_PORT = 6379

WAL_DIR = os.environ.get("EFDA_WAL_DIR", "/var/efda/wal")
WAL_MAX_BYTES = 5 * 1024 * 1024


class RedisError(Exception):
    pass


class RedisClient:
    """A small RESP client. Enough for SET, GET, KEYS, DEL, EXPIRE, PING."""

    def __init__(self, host=None, port=None, timeout=5.0):
        host = host or os.environ.get("EFDA_REDIS_HOST", DEFAULT_REDIS_HOST)
        port = int(port or os.environ.get("EFDA_REDIS_PORT", DEFAULT_REDIS_PORT))
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock = None
        self._buffer = b""

    def connect(self):
        if self._sock is not None:
            return self._sock
        try:
            self._sock = socket.create_connection(
                (self.host, self.port), timeout=self.timeout
            )
            self._sock.settimeout(self.timeout)
            self._buffer = b""
        except OSError as exc:
            raise RedisError(
                f"cannot reach redis at {self.host}:{self.port}: {exc}"
            ) from exc
        return self._sock

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None
                self._buffer = b""

    def _send(self, *args):
        payload = [f"*{len(args)}\r\n".encode()]
        for arg in args:
            raw = arg.encode() if isinstance(arg, str) else arg
            payload.append(b"$%d\r\n%s\r\n" % (len(raw), raw))
        self.connect().sendall(b"".join(payload))

    def _read_line(self) -> bytes:
        while b"\r\n" not in self._buffer:
            chunk = self.connect().recv(65536)
            if not chunk:
                raise RedisError("redis closed the connection")
            self._buffer += chunk
        line, self._buffer = self._buffer.split(b"\r\n", 1)
        return line

    def _read_exact(self, count: int) -> bytes:
        while len(self._buffer) < count:
            chunk = self.connect().recv(65536)
            if not chunk:
                raise RedisError("redis closed the connection")
            self._buffer += chunk
        data, self._buffer = self._buffer[:count], self._buffer[count:]
        return data

    def _read_reply(self):
        line = self._read_line()
        kind, rest = line[:1], line[1:]
        if kind == b"+":
            return rest.decode()
        if kind == b"-":
            raise RedisError(rest.decode())
        if kind == b":":
            return int(rest)
        if kind == b"$":
            length = int(rest)
            if length == -1:
                return None
            data = self._read_exact(length)
            self._read_exact(2)
            return data.decode()
        if kind == b"*":
            count = int(rest)
            if count == -1:
                return None
            return [self._read_reply() for _ in range(count)]
        raise RedisError(f"unknown reply type {kind!r}")

    def command(self, *args):
        self._send(*args)
        return self._read_reply()

    def ping(self) -> bool:
        try:
            return self.command("PING") == "PONG"
        except (RedisError, OSError):
            return False

    def set(self, key: str, value: str, ttl=None):
        if ttl:
            return self.command("SET", key, value, "EX", str(int(ttl)))
        return self.command("SET", key, value)

    def get(self, key: str):
        return self.command("GET", key)

    def delete(self, key: str):
        return self.command("DEL", key)

    def keys(self, pattern: str):
        return sorted(self.command("KEYS", pattern) or [])


def artifact_key(identity: dict) -> str:
    """The Redis key that holds an artifact, derived from its identity."""
    cluster = identity.get("cluster") or "unknown-cluster"
    namespace = identity.get("namespace") or "default"
    component_class = identity.get("component_class") or "unclassified"
    runner_id = identity.get("runner_id") or "unknown-runner"
    return f"efda:evidence:{cluster}:{namespace}:{component_class}:{runner_id}:artifact"


def checkpoint_key(runner_id: str) -> str:
    return f"efda:ckpt:{runner_id}"


def report_key(runner_id: str) -> str:
    """Where a DiagnosticReport waits for the executor."""
    return f"efda:report:{runner_id}"


def remediation_key(runner_id: str) -> str:
    """Where a RemediationArtifact lands."""
    return f"efda:remediation:{runner_id}"


class ArtifactStore:
    """Artifacts in Redis, with a local WAL when Redis is unreachable."""

    def __init__(self, redis_client=None, wal_dir=None):
        self.redis = redis_client
        self.wal_dir = wal_dir or WAL_DIR

    # -- WAL ------------------------------------------------------------
    def _wal_path(self, key: str) -> str:
        safe = key.replace(":", "_")
        return os.path.join(self.wal_dir, f"{safe}.jsonl")

    def wal_write(self, key: str, payload: str) -> str:
        os.makedirs(self.wal_dir, exist_ok=True)
        path = self._wal_path(key)
        try:
            if os.path.exists(path) and os.path.getsize(path) > WAL_MAX_BYTES:
                os.replace(path, path + ".overflow")
        except OSError:
            pass
        record = {"key": key, "payload": payload, "at": time.time()}
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return path

    def wal_entries(self, key: str):
        path = self._wal_path(key)
        if not os.path.exists(path):
            return []
        entries = []
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    entries.append(line)
                    continue
                if isinstance(record, dict) and "payload" in record:
                    entries.append(record["payload"])
                else:
                    entries.append(line)
        return entries

    def wal_keys(self):
        """Every key the WAL holds, so the drain knows where to push."""
        keys = []
        if not os.path.isdir(self.wal_dir):
            return keys
        for name in sorted(os.listdir(self.wal_dir)):
            if not name.endswith(".jsonl"):
                continue
            path = os.path.join(self.wal_dir, name)
            key = None
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                        except ValueError:
                            continue
                        if isinstance(record, dict) and record.get("key"):
                            key = record["key"]
                            break
            except OSError:
                continue
            if key:
                keys.append(key)
        return keys

    def wal_drain(self, key: str) -> int:
        """Push every WAL entry for this key into Redis, oldest first."""
        if self.redis is None:
            return 0
        entries = self.wal_entries(key)
        pushed = 0
        for entry in entries:
            try:
                self.redis.set(key, entry)
                pushed += 1
            except (RedisError, OSError):
                break
        if pushed and pushed == len(entries):
            try:
                os.remove(self._wal_path(key))
            except OSError:
                pass
        return pushed

    def wal_drain_all(self) -> dict:
        """Drain every key the WAL holds. The sink came back."""
        drained = {}
        for key in self.wal_keys():
            drained[key] = self.wal_drain(key)
        return drained

    # -- artifacts ------------------------------------------------------
    def write(self, artifact: dict, ttl_seconds=30 * 24 * 3600) -> str:
        """Store an artifact at its deterministic address.

        Returns the key. When the sink is unreachable the artifact is written
        to the WAL instead and the caller is told so by the ``ARTIFACT_WRITE_FAILED``
        sentinel on stderr -- the evidence is not lost silently.
        """
        identity = artifact.get("identity") or {}
        key = artifact_key(identity)
        payload = json.dumps(artifact, sort_keys=True)
        if self.redis is not None:
            try:
                self.redis.set(key, payload, ttl=ttl_seconds)
                self.wal_drain(key)
                return key
            except (RedisError, OSError) as exc:
                self.wal_write(key, payload)
                raise RedisError(f"artifact write failed, kept in WAL: {exc}") from exc
        self.wal_write(key, payload)
        return key

    def read(self, identity: dict) -> dict:
        key = artifact_key(identity)
        if self.redis is None:
            raise RedisError("no redis client")
        payload = self.redis.get(key)
        if payload is None:
            entries = self.wal_entries(key)
            if not entries:
                return None
            payload = entries[-1]
        return json.loads(payload)

    def read_by_key(self, key: str) -> dict:
        payload = self.redis.get(key) if self.redis else None
        if payload is None:
            entries = self.wal_entries(key)
            if not entries:
                return None
            payload = entries[-1]
        return json.loads(payload)

    def list_artifacts(self, component_class: str = None):
        pattern = "efda:evidence:*:artifact"
        keys = self.redis.keys(pattern) if self.redis else []
        artifacts = []
        for key in keys:
            try:
                artifact = self.read_by_key(key)
            except (ValueError, RedisError):
                continue
            if artifact is None:
                continue
            if component_class:
                identity = artifact.get("identity") or {}
                if identity.get("component_class") != component_class:
                    continue
            artifacts.append(artifact)
        return artifacts

    def address_of(self, artifact: dict) -> str:
        return artifact_address(artifact.get("identity") or {})

    # -- reports ---------------------------------------------------------
    def write_report(self, report: dict, runner_id: str, ttl_seconds=24 * 3600) -> str:
        key = report_key(runner_id)
        payload = json.dumps(report, sort_keys=True)
        if self.redis is not None:
            try:
                self.redis.set(key, payload, ttl=ttl_seconds)
                return key
            except (RedisError, OSError):
                pass
        self.wal_write(key, payload)
        return key

    def list_reports(self):
        keys = self.redis.keys("efda:report:*") if self.redis else []
        reports = []
        for key in keys:
            try:
                report = self.read_by_key(key)
            except (ValueError, RedisError):
                continue
            if report:
                report["_key"] = key
                reports.append(report)
        return reports

    def write_remediation(
        self, artifact: dict, runner_id: str, ttl_seconds=30 * 24 * 3600
    ) -> str:
        key = remediation_key(runner_id)
        payload = json.dumps(artifact, sort_keys=True)
        if self.redis is not None:
            try:
                self.redis.set(key, payload, ttl=ttl_seconds)
                return key
            except (RedisError, OSError):
                pass
        self.wal_write(key, payload)
        return key

    def remediated(self, runner_id: str) -> bool:
        if self.redis is None:
            return False
        try:
            return self.redis.get(remediation_key(runner_id)) is not None
        except (RedisError, OSError):
            return False


class CheckpointStore:
    """The L1 checkpoint sink: progress that survives the child's death."""

    def __init__(self, redis_client=None, wal_dir=None):
        self.redis = redis_client
        self.wal_dir = wal_dir or WAL_DIR

    def write(self, checkpoint: dict, ttl_seconds=24 * 3600) -> str:
        runner_id = checkpoint.get("runner_id", "unknown")
        key = checkpoint_key(runner_id)
        payload = json.dumps(checkpoint, sort_keys=True)
        if self.redis is not None:
            try:
                self.redis.set(key, payload, ttl=ttl_seconds)
                return key
            except (RedisError, OSError):
                pass
        store = ArtifactStore(self.redis, self.wal_dir)
        store.wal_write(key, payload)
        return key

    def read(self, runner_id: str):
        key = checkpoint_key(runner_id)
        if self.redis is not None:
            try:
                payload = self.redis.get(key)
                if payload:
                    return json.loads(payload)
            except (RedisError, OSError, ValueError):
                pass
        store = ArtifactStore(self.redis, self.wal_dir)
        entries = store.wal_entries(key)
        if not entries:
            return None
        return json.loads(entries[-1])


def wait_for_redis(host=None, port=None, attempts=10, delay=1.0) -> bool:
    """Block until the sink answers, or give up and say so."""
    client = RedisClient(host, port)
    for _ in range(max(1, attempts)):
        if client.ping():
            client.close()
            return True
        time.sleep(delay)
    client.close()
    return False
