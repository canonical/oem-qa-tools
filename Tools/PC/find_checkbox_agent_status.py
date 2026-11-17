#!/usr/bin/env python3

import argparse
import base64
import glob
import gzip
import json
import os
import sys
from pathlib import Path
from typing import Any, TypedDict

DEFAULT_SESSION_ROOT_DIR = Path("/var/tmp/checkbox-ng/sessions")
DEFAULT_AGENT_PORT = 18871

_USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"


def colorize_bool(value: bool) -> str:
    """Render a bool as green "True" / red "False" when writing to a
    terminal (honors the NO_COLOR convention and non-tty output)."""
    text = str(value)
    if not _USE_COLOR:
        return text
    color = _GREEN if value else _RED
    return f"{color}{text}{_RESET}"


FLAG_INCOMPLETE = "incomplete"
FLAG_SETTING_UP = "setting_up"
FLAG_BOOTSTRAPPING = "bootstrapping"
UNFINALIZED_FLAGS = frozenset(
    {FLAG_INCOMPLETE, FLAG_SETTING_UP, FLAG_BOOTSTRAPPING}
)


class SessionMetadata(TypedDict):
    testplan_id: str | None
    flags: frozenset[str]
    running_job_name: str | None
    # True when `running_job_name` has not yet recorded a result, meaning
    # checkbox started it but hasn't finished executing it. checkbox never
    # clears `running_job_name` back to None after a job finishes, so its
    # mere presence does NOT mean a job is still executing - it's just the
    # last job that was *started*.
    running_job_has_no_result: bool
    last_job_id: str | None


def get_valid_sessions(session_root_dir: Path) -> list[Path]:
    """Get a list of valid sessions under `session_root_dir`

    This is achieved by looking at which session directory has non-empty
    io-logs. If it's empty, it's either tossed by checkbox or didn't even
    reach the test case where it dumps the udev database, thus invalid
    """
    if not session_root_dir.exists():
        return []
    valid_session_dirs: list[Path] = []
    for d in os.listdir(session_root_dir):
        try:
            if len(os.listdir(session_root_dir / d / "io-logs")) != 0:
                valid_session_dirs.append(session_root_dir / d)
        except (FileNotFoundError, NotADirectoryError):
            continue
    return valid_session_dirs


def read_session_metadata(session_path: Path) -> SessionMetadata:
    """Read the bits of session metadata needed to determine whether a
    session is running and what the last job was.

    :param session_path: path to a session directory (must contain a
        "session" file, gzip-compressed JSON)
    """
    with gzip.open(session_path / "session", "rb") as arc:
        session_json: dict[str, Any] = json.load(arc)

    metadata: dict[str, Any] = session_json["session"]["metadata"]
    results: dict[str, Any] = session_json["session"].get("results", {})

    testplan_id: str | None = None
    app_blob_b64 = metadata.get("app_blob")
    if app_blob_b64:
        try:
            app_blob = json.loads(base64.b64decode(app_blob_b64))
            testplan_id = str(app_blob.get("testplan_id")) or None
        except Exception:
            testplan_id = None

    flags = frozenset(metadata.get("flags") or [])
    running_job_name = metadata.get("running_job_name")
    # `results` is a dict of job_id -> [attempts...], keys are stored in
    # execution order, so the last key is the last job that recorded a result
    last_completed_job = next(reversed(results), None) if results else None
    running_job_has_no_result = bool(
        running_job_name and running_job_name not in results
    )

    return SessionMetadata(
        testplan_id=testplan_id,
        flags=flags,
        running_job_name=running_job_name,
        running_job_has_no_result=running_job_has_no_result,
        last_job_id=running_job_name or last_completed_job,
    )


def find_running_session(
    session_root_dir: Path,
) -> tuple[Path, SessionMetadata] | None:
    running_sessions: list[tuple[float, Path, SessionMetadata]] = []
    for session_path in get_valid_sessions(session_root_dir):
        try:
            metadata = read_session_metadata(session_path)
        except Exception as e:
            print(
                f"Skipping unreadable session '{session_path}': {e!r}",
                file=sys.stderr,
            )
            continue
        if metadata["flags"] & UNFINALIZED_FLAGS:
            mtime = (session_path / "session").stat().st_mtime
            running_sessions.append((mtime, session_path, metadata))

    if not running_sessions:
        return None
    running_sessions.sort(key=lambda t: t[0], reverse=True)
    _, session_path, metadata = running_sessions[0]
    return session_path, metadata


class AgentInfo(TypedDict):
    pid: int
    port: int


def find_agent_processes() -> list[AgentInfo]:
    agents: list[AgentInfo] = []
    for cmdline_path in glob.glob("/proc/[0-9]*/cmdline"):
        try:
            with open(cmdline_path, "rb") as f:
                raw = f.read()
        except (FileNotFoundError, PermissionError):
            # process may have exited mid-scan, or we lack permission
            continue
        args = [a.decode(errors="replace") for a in raw.split(b"\0") if a]
        if (
            not any("checkbox-cli" in a for a in args)
            or "run-agent" not in args
        ):
            continue

        port = DEFAULT_AGENT_PORT
        if "--port" in args:
            try:
                port = int(args[args.index("--port") + 1])
            except (IndexError, ValueError):
                pass

        pid = int(cmdline_path.split("/")[2])
        agents.append(AgentInfo(pid=pid, port=port))
    return agents


class PortConnectionInfo(TypedDict):
    listening: bool
    established_remote_addrs: list[str]


def _decode_hex_addr(hex_addr: str) -> tuple[str, int]:
    """Decode an "IP:PORT" pair as found in /proc/net/tcp{,6}"""
    ip_hex, port_hex = hex_addr.split(":")
    port = int(port_hex, 16)
    byte_order = bytes.fromhex(ip_hex)
    # group into 4-byte (IPv4) or 16-byte (IPv6) little-endian words
    ip_bytes = bytearray()
    for i in range(0, len(byte_order), 4):
        ip_bytes.extend(reversed(byte_order[i : i + 4]))
    if len(ip_bytes) == 4:
        ip = ".".join(str(b) for b in ip_bytes)
    else:
        ip = ":".join(
            f"{ip_bytes[i]:02x}{ip_bytes[i + 1]:02x}" for i in range(0, 16, 2)
        )
    return ip, port


def get_port_connection_info(port: int) -> PortConnectionInfo:
    listening = False
    established_remote_addrs: list[str] = []

    for proc_file in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            with open(proc_file) as f:
                lines = f.readlines()[1:]  # skip header
        except FileNotFoundError:
            continue
        for line in lines:
            fields = line.split()
            if len(fields) < 4:
                continue
            local_addr, remote_addr, state = fields[1], fields[2], fields[3]
            _local_ip, local_port = _decode_hex_addr(local_addr)
            if local_port != port:
                continue
            if state == "0A":  # TCP_LISTEN
                listening = True
            elif state == "01":  # TCP_ESTABLISHED
                remote_ip, remote_port = _decode_hex_addr(remote_addr)
                established_remote_addrs.append(f"{remote_ip}:{remote_port}")

    return PortConnectionInfo(
        listening=listening, established_remote_addrs=established_remote_addrs
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Find the currently running checkbox-ng session, the last job "
            "that was run in it, and whether a controller is currently "
            "connected to the agent."
        )
    )
    parser.add_argument(
        "--json", action="store_true", help="Print output in JSON format"
    )
    parser.add_argument(
        "--session-root",
        type=Path,
        default=DEFAULT_SESSION_ROOT_DIR,
        help=f"Override the session root directory (default: {DEFAULT_SESSION_ROOT_DIR})",
    )
    parser.add_argument(
        "--agent-port",
        type=int,
        default=None,
        help=(
            "Override the port to check for an agent/controller connection "
            f"(default: {DEFAULT_AGENT_PORT}, or auto-detected from the "
            "running `checkbox-cli run-agent` process if found)"
        ),
    )
    args = parser.parse_args()

    agents = find_agent_processes()
    agent_running = len(agents) > 0
    agent_port = (
        args.agent_port
        if args.agent_port is not None
        else (agents[0]["port"] if agents else DEFAULT_AGENT_PORT)
    )
    conn_info = get_port_connection_info(agent_port)
    controller_connected = bool(conn_info["established_remote_addrs"])

    found = find_running_session(args.session_root)
    session_path, metadata = (None, None) if found is None else found

    job_actually_running = bool(
        agent_running
        and controller_connected
        and metadata is not None
        and metadata["running_job_has_no_result"]
    )

    if args.json:
        print(
            json.dumps(
                {
                    "agent_running": agent_running,
                    "agent_port": agent_port,
                    "controller_connected": controller_connected,
                    "controller_addrs": conn_info["established_remote_addrs"],
                    "session_path": (
                        str(session_path) if session_path else None
                    ),
                    "test_plan": metadata["testplan_id"] if metadata else None,
                    "last_job": metadata["last_job_id"] if metadata else None,
                    "job_actually_running": job_actually_running,
                    "flags": sorted(metadata["flags"]) if metadata else [],
                }
            )
        )
        return

    print(
        f"Agent running: {colorize_bool(agent_running)}"
        + (f" (pid(s): {[a['pid'] for a in agents]})" if agents else "")
    )
    print(f"Agent port: {agent_port}")
    print(
        f"Controller connected: {colorize_bool(controller_connected)}", end=""
    )
    print(
        f" (from {', '.join(conn_info['established_remote_addrs'])})"
        if controller_connected
        else ""
    )

    if metadata is None:
        print(
            "No running/incomplete checkbox session was found on this device"
        )
        return

    print(f"Session directory: {session_path}")
    print(f"Test Plan: {metadata['testplan_id']}")
    print(f"Flags: {', '.join(sorted(metadata['flags'])) or '(none)'}")
    if metadata["last_job_id"] is None:
        print("Last Job: None")
    elif job_actually_running:
        print(f"Currently Running Job: {metadata['last_job_id']}")
    else:
        print(f"Last Job (not actively running): {metadata['last_job_id']}")


if __name__ == "__main__":
    main()
