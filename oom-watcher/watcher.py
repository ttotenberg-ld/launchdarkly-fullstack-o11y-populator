"""
OOM watcher — tails the host kernel ring buffer for cgroup OOM kills,
resolves the killing cgroup back to a docker container name, and emits
the event as a structured OTel log via the LaunchDarkly Observability
plugin so it shows up in the same place as the application traces.

Lives outside the per-service observability config because it's a host-level
signal that any container can be the subject of. Runs with pid:host so
dmesg/journalctl see the kernel log, and with a read-only docker.sock
mount so we can resolve cgroup container IDs to compose service names.
"""

import os
import re
import sys
import time
import signal
import subprocess
from datetime import datetime
from typing import Optional

import docker
import ldclient
from ldclient.config import Config
from ldobserve import ObservabilityConfig, ObservabilityPlugin
from opentelemetry import trace
from opentelemetry._logs import get_logger, set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LogRecord
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

SERVICE_NAME = "oom-watcher"
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
LD_SDK_KEY = os.getenv("LD_SDK_KEY")

# Kernel OOM-kill lines look like:
#   oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=docker-<cid>.scope,...,task=chrome-headless,pid=12345,uid=0
# We pull out the constraint, the cgroup container ID, the task name, and the pid.
OOM_KILL_RE = re.compile(
    r"oom-kill:constraint=(?P<constraint>\S+?),"
    r".*?cpuset=docker-(?P<cid>[0-9a-f]+)\.scope,"
    r".*?task=(?P<task>\S+?),"
    r"pid=(?P<pid>\d+)",
)

# Followup line carries RSS info:
#   Memory cgroup out of memory: Killed process 12345 (chrome-headless) total-vm:...kB, anon-rss:...kB, ...
KILLED_RE = re.compile(
    r"Killed process (?P<pid>\d+) \((?P<proc>[^)]+)\) "
    r"total-vm:(?P<total_vm>\d+)kB, "
    r"anon-rss:(?P<anon_rss>\d+)kB, "
    r"file-rss:(?P<file_rss>\d+)kB"
)


def init_ld_logger():
    """Wire up the LD ObservabilityPlugin and grab a logger that ships to LD."""
    if not LD_SDK_KEY:
        print("ERROR: LD_SDK_KEY not set — refusing to start", file=sys.stderr)
        sys.exit(2)

    plugin = ObservabilityPlugin(
        ObservabilityConfig(
            service_name=SERVICE_NAME,
            service_version=SERVICE_VERSION,
            environment=ENVIRONMENT,
            # No web framework to instrument; we only need the plugin for its
            # OTel exporter setup wiring against the LD endpoint.
            disabled_instrumentations=["flask", "requests"],
        )
    )
    ldclient.set_config(Config(sdk_key=LD_SDK_KEY, plugins=[plugin]))
    # Touch the client so the plugin's tracer/logger providers actually init.
    _ = ldclient.get()
    return get_logger(SERVICE_NAME)


def get_docker_client() -> Optional[docker.DockerClient]:
    """Return a docker client or None if the socket isn't available."""
    try:
        return docker.from_env()
    except Exception as e:
        print(f"WARN: docker client unavailable: {e}", file=sys.stderr)
        return None


def resolve_container(client: Optional[docker.DockerClient], cid: str) -> dict:
    """Resolve a 64-char container ID prefix to a name + compose service."""
    if not client:
        return {"container.id": cid}
    try:
        c = client.containers.get(cid[:12])
        labels = c.labels or {}
        return {
            "container.id": cid,
            "container.name": c.name,
            "container.image": (c.image.tags[0] if c.image and c.image.tags else ""),
            "container.compose.service": labels.get("com.docker.compose.service", ""),
            "container.compose.project": labels.get("com.docker.compose.project", ""),
        }
    except docker.errors.NotFound:
        # Container may already be gone by the time we resolve.
        return {"container.id": cid}
    except Exception as e:
        print(f"WARN: resolve_container({cid[:12]}) failed: {e}", file=sys.stderr)
        return {"container.id": cid}


def tail_dmesg():
    """Yield each kernel ring-buffer line as it arrives.

    `dmesg --follow` blocks for new entries; `--time-format iso` gives us
    a parseable timestamp so we don't have to compute one from --human.
    """
    # -w: follow; -T disabled in favor of explicit iso timestamps.
    proc = subprocess.Popen(
        ["dmesg", "--follow", "--time-format", "iso"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    try:
        for line in proc.stdout:
            yield line.rstrip("\n")
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            pass


def main():
    logger = init_ld_logger()
    docker_client = get_docker_client()
    print(f"[oom-watcher] started ({SERVICE_NAME} v{SERVICE_VERSION} env={ENVIRONMENT})", flush=True)
    print(f"[oom-watcher] tailing dmesg; docker={'connected' if docker_client else 'unavailable'}", flush=True)

    # Pending OOM event waiting for its "Killed process" follow-up line.
    pending: Optional[dict] = None

    def shutdown(_signum, _frame):
        print("[oom-watcher] shutdown signal received", flush=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    for raw in tail_dmesg():
        try:
            m = OOM_KILL_RE.search(raw)
            if m:
                pending = m.groupdict()
                pending["raw"] = raw
                continue

            k = KILLED_RE.search(raw)
            if k and pending:
                fields = {**pending, **k.groupdict()}
                cid = fields.get("cid", "")
                container = resolve_container(docker_client, cid) if cid else {}

                attrs = {
                    "event.name": "kernel.oom_kill",
                    "kernel.oom.constraint": fields.get("constraint", ""),
                    "kernel.oom.task": fields.get("task", ""),
                    "kernel.oom.killed_process": fields.get("proc", ""),
                    "kernel.oom.killed_pid": int(fields.get("pid", "0") or 0),
                    "kernel.oom.killed_total_vm_kb": int(fields.get("total_vm", "0") or 0),
                    "kernel.oom.killed_anon_rss_kb": int(fields.get("anon_rss", "0") or 0),
                    "kernel.oom.killed_file_rss_kb": int(fields.get("file_rss", "0") or 0),
                    **container,
                }
                body = (
                    f"OOM kill: {fields.get('proc')} pid={fields.get('pid')} "
                    f"anon_rss={int(fields.get('anon_rss', 0)) // 1024}MB "
                    f"in container={container.get('container.name', cid[:12])}"
                )
                print(f"[oom-watcher] {body}", flush=True)
                logger.emit(
                    LogRecord(
                        timestamp=int(time.time() * 1e9),
                        severity_text="ERROR",
                        severity_number=17,  # ERROR
                        body=body,
                        attributes=attrs,
                    )
                )
                pending = None
        except Exception as e:
            print(f"[oom-watcher] parse error: {e} line={raw!r}", flush=True)
            pending = None


if __name__ == "__main__":
    main()
