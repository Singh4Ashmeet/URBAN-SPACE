#!/usr/bin/env python3
"""UrbanShield local project launcher.

This script intentionally uses only the Python standard library so it can run
on Windows, macOS, and Linux without creating a Python virtual environment.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / ".urbanshield"
LOG_DIR = RUNTIME_DIR / "logs"
PID_FILE = RUNTIME_DIR / "pids.json"
LOCAL_REQUIRED_PATHS = ["core-api", "simulation-service", "ai-service", "frontend", "local-runtime"]
DOCKER_REQUIRED_PATHS = ["core-service", "core-api", "simulation-service", "ai-service", "frontend", "local-runtime", "docker-compose.yml"]
HEALTH_URLS = {
    "core-api": "http://127.0.0.1:8000/core/api/core/health",
    "simulation-service": "http://127.0.0.1:8000/simulation/api/simulation/health",
    "ai-service": "http://127.0.0.1:8000/ai/api/ai/health",
    "frontend": "http://127.0.0.1:3000",
}
SERVICE_PORTS = {
    "core-api": 8080,
    "simulation-service": 8002,
    "ai-service": 8010,
    "gateway": 8000,
    "frontend": 3000,
}


def run(command: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=check,
    )


def write_console(text: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def run_quiet(command: list[str], cwd: Path, failure_message: str, timeout_seconds: int = 180) -> None:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        if error.stdout:
            output = error.stdout if isinstance(error.stdout, str) else error.stdout.decode("utf-8", errors="replace")
            write_console(output)
        fail(f"{failure_message} Command timed out after {timeout_seconds} seconds.")
    if result.returncode != 0:
        write_console(result.stdout)
        fail(failure_message)


def project_python() -> str:
    venv_python = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return str(venv_python) if venv_python.exists() else sys.executable


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def ensure_runtime_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def install_local_dependencies(force: bool = False) -> None:
    ensure_runtime_dirs()
    python_exe = project_python()
    if not (ROOT / ".venv").exists():
        print("Creating local Python virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(ROOT / ".venv")], cwd=ROOT, check=True)
        python_exe = project_python()
    marker = RUNTIME_DIR / "python-deps-installed"
    if force or not marker.exists():
        print("Installing Python dependencies...")
        run_quiet(
            [python_exe, "-m", "pip", "install", "-r", str(ROOT / "simulation-service/requirements.txt")],
            ROOT,
            "Python dependency installation failed.",
        )
        run_quiet(
            [python_exe, "-m", "pip", "install", "-r", str(ROOT / "core-api/requirements.txt")],
            ROOT,
            "Core API dependency installation failed.",
        )
        run_quiet(
            [python_exe, "-m", "pip", "install", "-r", str(ROOT / "ai-service/requirements.txt")],
            ROOT,
            "AI service dependency installation failed.",
        )
        marker.write_text(str(time.time()), encoding="utf-8")

    frontend_node_modules = ROOT / "frontend" / "node_modules"
    if force or not frontend_node_modules.exists():
        print("Installing frontend dependencies...")
        run_quiet([npm_command(), "ci"], ROOT / "frontend", "Frontend dependency installation failed.")


def load_pids() -> dict[str, int]:
    if not PID_FILE.exists():
        return {}
    try:
        return json.loads(PID_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_pids(pids: dict[str, int]) -> None:
    ensure_runtime_dirs()
    PID_FILE.write_text(json.dumps(pids, indent=2), encoding="utf-8")


def clear_pids() -> None:
    if not PID_FILE.exists():
        return
    try:
        PID_FILE.unlink()
    except OSError as error:
        try:
            PID_FILE.write_text("{}", encoding="utf-8")
            print(f"Could not remove {PID_FILE.relative_to(ROOT)} ({error}); cleared recorded PIDs instead.")
        except OSError as write_error:
            print(f"Could not clear {PID_FILE.relative_to(ROOT)}: {write_error}")


def is_pid_running(pid: int) -> bool:
    if os.name == "nt":
        result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def pids_for_port(port: int) -> list[int]:
    if os.name != "nt":
        return []
    result = subprocess.run(["netstat", "-ano", "-p", "tcp"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    pids: list[int] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1].endswith(f":{port}") and parts[3].upper() == "LISTENING":
            try:
                pid = int(parts[4])
            except ValueError:
                continue
            if pid not in pids:
                pids.append(pid)
    return pids


def pid_for_port(port: int) -> int | None:
    pids = pids_for_port(port)
    return pids[0] if pids else None


def stop_process(pid: int) -> None:
    if not is_pid_running(pid):
        return
    if os.name == "nt":
        result = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if result.returncode != 0:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
    else:
        os.kill(pid, signal.SIGTERM)


def stop_port(port: int) -> None:
    for pid in pids_for_port(port):
        stop_process(pid)


def stop_local_stack() -> None:
    pids = load_pids()
    if not pids:
        print("No local UrbanShield processes are recorded.")
    for name, pid in pids.items():
        print(f"Stopping {name} ({pid})...")
        stop_process(pid)
    for name, port in SERVICE_PORTS.items():
        for pid in pids_for_port(port):
            print(f"Stopping {name} listener on port {port} ({pid})...")
            stop_process(pid)
    clear_pids()


def free_local_ports() -> None:
    for name, port in SERVICE_PORTS.items():
        for pid in pids_for_port(port):
            print(f"Freeing {name} port {port} (PID {pid})...")
            stop_process(pid)


def start_process(name: str, command: list[str], cwd: Path) -> int:
    ensure_runtime_dirs()
    log_file = LOG_DIR / f"{name}.log"
    log_handle = log_file.open("a", encoding="utf-8")
    log_handle.write(f"\n--- starting {name}: {' '.join(command)} ---\n")
    log_handle.flush()
    popen_kwargs: dict[str, object] = {
        "cwd": cwd,
        "stdin": subprocess.DEVNULL,
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
    }
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        popen_kwargs["startupinfo"] = startupinfo
    else:
        popen_kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **popen_kwargs)
    print(f"Started {name} on PID {process.pid}. Log: {log_file.relative_to(ROOT)}")
    return process.pid


def build_local_frontend() -> None:
    clean_frontend_build()
    prepare_frontend_build_dir(ROOT / "frontend" / ".next")
    print("Building frontend...")
    run_quiet([npm_command(), "run", "build"], ROOT / "frontend", "Frontend build failed.")


def build_frontend_for_validation() -> None:
    if os.name == "nt":
        build_frontend_for_validation_copy()
        return
    dist_dir = f".next-validation-{int(time.time())}"
    prepare_frontend_build_dir(ROOT / "frontend" / dist_dir)
    print(f"Building frontend validation output in {dist_dir}...")
    env = os.environ.copy()
    env["NEXT_DIST_DIR"] = dist_dir
    result = subprocess.run(
        [npm_command(), "run", "build", "--", "--webpack"],
        cwd=ROOT / "frontend",
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=240,
    )
    if result.returncode != 0:
        write_console(result.stdout)
        fail("Frontend build failed.")


def build_frontend_for_validation_copy() -> None:
    source_frontend = ROOT / "frontend"
    source_node_modules = source_frontend / "node_modules"
    if not source_node_modules.exists():
        fail("Frontend dependencies are missing. Run `npm ci` in frontend first.")

    temp_root = create_validation_temp_root()
    temp_frontend = temp_root / "frontend"
    print(f"Building frontend validation output in a temporary Windows-safe directory: {temp_frontend}")

    def ignore_generated(_directory: str, names: list[str]) -> set[str]:
        ignored = {"node_modules", "out", "tsconfig.tsbuildinfo"}
        ignored.update(name for name in names if name == ".next" or name.startswith(".next-"))
        return ignored

    try:
        try:
            shutil.copytree(source_frontend, temp_frontend, ignore=ignore_generated)
            link_frontend_node_modules(source_node_modules, temp_frontend / "node_modules")
        except OSError as error:
            fail(
                "Could not prepare a temporary frontend validation build directory. "
                f"Windows reported: {error}. "
                "Set URBANSHIELD_VALIDATION_TEMP to a writable folder outside OneDrive or move the repository to a normal development directory."
            )
        env = os.environ.copy()
        env["NEXT_DIST_DIR"] = ".next-validation"
        result = subprocess.run(
            [npm_command(), "run", "build", "--", "--webpack"],
            cwd=temp_frontend,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=240,
        )
        if result.returncode != 0:
            write_console(result.stdout)
            fail("Frontend build failed.")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def create_validation_temp_root() -> Path:
    configured = os.environ.get("URBANSHIELD_VALIDATION_TEMP")
    if configured:
        parent = Path(configured).expanduser().resolve()
        parent.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="urbanshield-frontend-build-", dir=parent))
    return Path(tempfile.mkdtemp(prefix="urbanshield-frontend-build-"))


def link_frontend_node_modules(source: Path, target: Path) -> None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(target), str(source)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        if result.returncode != 0:
            write_console(result.stdout)
            fail("Could not link frontend node_modules into the validation build directory.")
    else:
        target.symlink_to(source, target_is_directory=True)


def prepare_frontend_build_dir(build_dir: Path, recursive: bool = False) -> None:
    build_dir.mkdir(parents=True, exist_ok=True)
    frontend_dir = (ROOT / "frontend").resolve()
    target = build_dir.resolve()
    if not str(target).startswith(str(frontend_dir)):
        fail(f"Refusing to adjust build directory outside frontend: {target}")
    if os.name != "nt":
        return

    icacls = shutil.which("icacls")
    if not icacls:
        return
    whoami = subprocess.run(["whoami"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    identity = whoami.stdout.strip()
    common = [str(target)]
    suffix = ["/T"] if recursive else []
    subprocess.run([icacls, *common, "/inheritance:d", *suffix], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    subprocess.run([icacls, *common, "/remove:g", "Everyone", *suffix], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    if identity:
        subprocess.run([icacls, *common, "/grant:r", f"{identity}:(OI)(CI)F", *suffix], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def clean_frontend_build() -> None:
    build_dir = ROOT / "frontend" / ".next"
    if not build_dir.exists():
        return
    frontend_dir = (ROOT / "frontend").resolve()
    target = build_dir.resolve()
    if not str(target).startswith(str(frontend_dir)):
        fail(f"Refusing to remove build directory outside frontend: {target}")
    prepare_frontend_build_dir(build_dir, recursive=True)
    try:
        shutil.rmtree(target)
    except OSError as error:
        if os.name != "nt":
            raise
        print(f"Python cleanup could not remove {build_dir.relative_to(ROOT)} ({error}); retrying with Windows cleanup.")
        powershell = Path(os.environ.get("SystemRoot", "C:\\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        command = (
            f"$target = Resolve-Path -LiteralPath '{target}'; "
            f"$frontend = Resolve-Path -LiteralPath '{frontend_dir}'; "
            "if (-not ($target.Path.StartsWith($frontend.Path))) { "
            "throw \"Refusing to remove outside frontend\" "
            "}; "
            "Remove-Item -LiteralPath $target.Path -Recurse -Force"
        )
        result = subprocess.run([str(powershell), "-NoProfile", "-Command", command], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode != 0:
            sys.stdout.write(result.stdout)
            fail("Frontend build cleanup failed.")


def frontend_build_exists() -> bool:
    return (ROOT / "frontend" / ".next").exists()


def start_local_stack(force_install: bool = False, production_frontend: bool = False) -> None:
    check_local_environment()
    ensure_env_files()
    stopped_before_install = False
    if force_install or production_frontend:
        stop_local_stack()
        free_local_ports()
        stopped_before_install = True
    install_local_dependencies(force_install)
    use_production_frontend = production_frontend or os.name == "nt"
    if use_production_frontend and (production_frontend or not frontend_build_exists()):
        build_local_frontend()
    if not stopped_before_install:
        stop_local_stack()
        free_local_ports()

    python_exe = project_python()
    frontend_command = [npm_command(), "run", "dev", "--", "-p", "3000"]
    if use_production_frontend:
        standalone_js = ROOT / "frontend" / ".next" / "standalone" / "server.js"
        if standalone_js.exists():
            standalone_dir = ROOT / "frontend" / ".next" / "standalone"
            public_src = ROOT / "frontend" / "public"
            public_dst = standalone_dir / "public"
            static_src = ROOT / "frontend" / ".next" / "static"
            static_dst = standalone_dir / ".next" / "static"
            try:
                if public_src.exists():
                    if public_dst.exists():
                        shutil.rmtree(public_dst, ignore_errors=True)
                    shutil.copytree(public_src, public_dst)
                if static_src.exists():
                    if static_dst.exists():
                        shutil.rmtree(static_dst, ignore_errors=True)
                    shutil.copytree(static_src, static_dst)
            except Exception as e:
                print(f"Warning: Failed to copy standalone assets: {e}")
            frontend_command = ["node", ".next/standalone/server.js"]
        else:
            frontend_command = [npm_command(), "run", "start", "--", "-p", "3000"]
    pids = {
        "core-api": start_process(
            "core-api",
            [python_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8080"],
            ROOT / "core-api",
        ),
        "simulation-service": start_process(
            "simulation-service",
            [python_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8002"],
            ROOT / "simulation-service",
        ),
        "ai-service": start_process(
            "ai-service",
            [python_exe, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010"],
            ROOT / "ai-service",
        ),
        "gateway": start_process(
            "gateway",
            [python_exe, "-m", "uvicorn", "gateway:app", "--host", "127.0.0.1", "--port", "8000"],
            ROOT / "local-runtime",
        ),
        "frontend": start_process(
            "frontend",
            frontend_command,
            ROOT / "frontend",
        ),
    }
    save_pids(pids)
    if not poll_health():
        show_local_logs()
        fail("One or more local services failed to become ready.")
    show_summary(mode="local")


def check_local_environment() -> None:
    print(f"Python: {sys.version.split()[0]}")
    if not shutil.which("npm"):
        fail("npm is not installed or is not on PATH. Install Node.js 20+.")
    missing = [path for path in LOCAL_REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        fail(f"Required project files are missing: {', '.join(missing)}")


def local_status() -> None:
    pids = load_pids()
    if not pids:
        print("No local UrbanShield processes are recorded.")
    for name, port in SERVICE_PORTS.items():
        recorded_pid = pids.get(name)
        port_pids = pids_for_port(port)
        if port_pids:
            print(f"{name}: running on port {port} (PIDs {', '.join(str(pid) for pid in port_pids)})")
        elif recorded_pid is not None:
            status = "running" if is_pid_running(recorded_pid) else "stopped"
            print(f"{name}: {status} (recorded PID {recorded_pid})")
        else:
            print(f"{name}: stopped")


def timed_health_check(name: str, url: str) -> dict[str, object]:
    started = time.perf_counter()
    try:
        with urlopen(url, timeout=5) as response:
            return {
                "name": name,
                "url": url,
                "status": "UP" if response.status < 500 else "DEGRADED",
                "http_status": response.status,
                "response_time_ms": round((time.perf_counter() - started) * 1000, 2),
            }
    except (URLError, TimeoutError, socket.timeout, OSError) as error:
        return {
            "name": name,
            "url": url,
            "status": "DOWN",
            "error": str(error),
            "response_time_ms": round((time.perf_counter() - started) * 1000, 2),
        }


def local_health_report() -> None:
    print("UrbanShield health report")
    print("")
    pids = load_pids()
    port_states: list[bool] = []
    for name, port in SERVICE_PORTS.items():
        recorded_pid = pids.get(name)
        port_pids = pids_for_port(port)
        pid = port_pids[0] if port_pids else recorded_pid
        state = "running" if port_pids or (pid and is_pid_running(pid)) else "stopped"
        port_states.append(state == "running")
        pid_label = f" (PIDs {', '.join(str(item) for item in port_pids)})" if port_pids else (f" (PID {pid})" if pid else "")
        print(f"- {name}: {state} on port {port}{pid_label}")
    print("")
    health_results: list[dict[str, object]] = []
    for name, url in HEALTH_URLS.items():
        result = timed_health_check(name, url)
        health_results.append(result)
        extra = f"HTTP {result['http_status']}" if "http_status" in result else result.get("error", "")
        print(f"- {name}: {result['status']} {extra} in {result['response_time_ms']} ms")
    gateway = timed_health_check("gateway", "http://127.0.0.1:8000/health")
    health_results.append(gateway)
    print(f"- gateway: {gateway['status']} in {gateway['response_time_ms']} ms")
    services = timed_health_check("gateway-services", "http://127.0.0.1:8000/health/services")
    health_results.append(services)
    print(f"- gateway-services: {services['status']} in {services['response_time_ms']} ms")
    print("")
    running = all(port_states) and all(result.get("status") == "UP" for result in health_results)
    show_summary(mode="local", running=running)


def run_local_tests() -> None:
    print("Stopping local stack before validation...")
    stop_local_stack()
    free_local_ports()
    print("Running frontend typecheck...")
    run_quiet([npm_command(), "run", "typecheck"], ROOT / "frontend", "Frontend typecheck failed.")
    print("Running frontend lint...")
    run_quiet([npm_command(), "run", "lint"], ROOT / "frontend", "Frontend lint failed.")
    print("Running frontend tests...")
    run_quiet([npm_command(), "test"], ROOT / "frontend", "Frontend tests failed.")
    print("Running frontend production build...")
    build_frontend_for_validation()
    print("Running core-api tests...")
    run_quiet([project_python(), "-m", "pytest"], ROOT / "core-api", "Core API tests failed.")
    print("Running simulation-service tests...")
    run_quiet([project_python(), "-m", "pytest"], ROOT / "simulation-service", "Simulation-service tests failed.")
    print("Running ai-service tests...")
    run_quiet([project_python(), "-m", "pytest"], ROOT / "ai-service", "AI service tests failed.")
    print("Running gateway integration tests...")
    run_quiet([project_python(), "-m", "unittest", "discover", "-s", "tests/integration"], ROOT, "Gateway integration tests failed.", timeout_seconds=240)
    print("All available local tests passed.")


def run_core_api_cli(command: str, *extra: str) -> None:
    run_quiet([project_python(), "-m", "app.cli", command, *extra], ROOT / "core-api", f"Core API {command} failed.")


def train_models() -> None:
    fail("--train-models requires the Phase 4 ml-service, which is not implemented in this local foundation yet.")


def show_local_logs() -> None:
    if not LOG_DIR.exists():
        print("No local logs yet.")
        return
    for log_file in sorted(LOG_DIR.glob("*.log")):
        print(f"\n--- {log_file.relative_to(ROOT)} ---")
        try:
            text = "\n".join(log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-40:])
            encoding = sys.stdout.encoding or "utf-8"
            sys.stdout.write(text.encode(encoding, errors="replace").decode(encoding, errors="replace") + "\n")
        except OSError as error:
            print(error)


def find_compose() -> list[str]:
    docker = shutil.which("docker")
    if not docker:
        fail("Docker is not installed or is not on PATH.")
    docker_command = find_working_docker_command(docker)
    probe = run(docker_command + ["compose", "version"], check=False)
    if probe.returncode == 0:
        return docker_command + ["compose"]
    legacy = shutil.which("docker-compose")
    if legacy:
        return [legacy]
    fail("Docker Compose is not available. Install Docker Desktop or Docker Compose.")


def find_working_docker_command(docker: str) -> list[str]:
    candidates = [[docker], [docker, "--context", "default"], [docker, "--context", "desktop-linux"]]
    working = first_working_docker_command(candidates)
    if working:
        return working

    maybe_start_docker_desktop()
    working = wait_for_docker(candidates)
    if working:
        return working

    fail("Docker daemon is not running or no Docker context is reachable. Start Docker Desktop and try again.")


def first_working_docker_command(candidates: list[list[str]]) -> list[str] | None:
    for candidate in candidates:
        probe = run(candidate + ["info"], check=False)
        if probe.returncode == 0:
            return candidate
    return None


def maybe_start_docker_desktop() -> None:
    if os.name != "nt":
        return
    docker_desktop = Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Docker" / "Docker" / "Docker Desktop.exe"
    if docker_desktop.exists():
        print("Docker daemon is not ready. Launching Docker Desktop...")
        subprocess.Popen([str(docker_desktop)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for_docker(candidates: list[list[str]], timeout_seconds: int = 120) -> list[str] | None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        working = first_working_docker_command(candidates)
        if working:
            return working
        print("Waiting for Docker daemon...")
        time.sleep(5)
    return None


def fail(message: str, code: int = 1) -> None:
    print(f"\nERROR: {message}")
    sys.exit(code)


def check_environment(compose: list[str]) -> None:
    print(f"Python: {sys.version.split()[0]}")
    if not shutil.which("docker"):
        fail("Docker is not installed.")
    docker_command = compose[:-1] if compose[-1] == "compose" else [compose[0]]
    daemon = run(docker_command + ["info"], check=False)
    if daemon.returncode != 0:
        fail("Docker daemon is not running. Start Docker Desktop or your Docker service.")
    missing = [path for path in DOCKER_REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        fail(f"Required project files are missing: {', '.join(missing)}")


def ensure_env_files() -> None:
    for example in [ROOT / ".env.example", ROOT / "frontend/.env.example", ROOT / "core-service/.env.example", ROOT / "simulation-service/.env.example"]:
        target = example.with_name(".env")
        if example.exists() and not target.exists():
            target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"Created {target.relative_to(ROOT)} from example.")


def compose_up(compose: list[str], force_build: bool) -> None:
    command = compose + ["up", "-d"]
    if force_build:
        command.append("--build")
    else:
        command.extend(["--build"])
    print("Starting UrbanShield containers...")
    result = run(command, check=False)
    print(result.stdout)
    if result.returncode != 0:
        fail("Docker Compose failed to start the stack.")


def poll_health(timeout_seconds: int = 180) -> bool:
    deadline = time.time() + timeout_seconds
    pending = set(HEALTH_URLS)
    while pending and time.time() < deadline:
        for name in list(pending):
            try:
                with urlopen(HEALTH_URLS[name], timeout=5) as response:
                    if response.status < 500:
                        print(f"Ready: {name}")
                        pending.remove(name)
            except (URLError, TimeoutError, socket.timeout, ConnectionError, OSError):
                pass
        if pending:
            print(f"Waiting for: {', '.join(sorted(pending))}")
            time.sleep(5)
    if pending:
        print(f"Timed out waiting for: {', '.join(sorted(pending))}")
        return False
    return True


def show_summary(mode: str = "docker", running: bool = True) -> None:
    print("\nUrbanShield is running." if running else "\nUrbanShield local URLs:")
    for name, url in HEALTH_URLS.items():
        print(f"- {name}: {url}")
    if mode == "docker":
        print("- Kong admin: http://localhost:8001")
    else:
        print("- Local gateway: http://127.0.0.1:8000")
    direct_core_label = "Direct core service" if mode == "docker" else "Direct local core API"
    print(f"- {direct_core_label}: http://127.0.0.1:8080")
    print("- Direct simulation service: http://127.0.0.1:8002")


def show_logs(compose: list[str], follow: bool) -> None:
    command = compose + ["logs"]
    if follow:
        command.append("-f")
    subprocess.run(command, cwd=ROOT, check=False)


def status(compose: list[str]) -> None:
    print(run(compose + ["ps"], check=False).stdout)


def stop(compose: list[str]) -> None:
    print(run(compose + ["down"], check=False).stdout)


def clean(compose: list[str]) -> None:
    answer = input("Remove database volumes too? Type 'delete volumes' to confirm: ").strip()
    command = compose + ["down", "--remove-orphans"]
    if answer == "delete volumes":
        command.append("-v")
    print(run(command, check=False).stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Start and manage UrbanShield.")
    parser.add_argument("--docker", action="store_true", help="Use Docker Compose instead of the local no-Docker runner.")
    parser.add_argument("--mode", choices=["local", "docker"], default="local", help="Choose local subprocess mode or Docker Compose mode.")
    parser.add_argument("--profile", choices=["minimal", "full"], default="minimal", help="Select the runtime profile. Local mode currently supports the minimal profile.")
    parser.add_argument("--build", action="store_true", help="Build before starting. Local mode builds and runs the production frontend; Docker mode rebuilds images.")
    parser.add_argument("--logs", action="store_true", help="Follow logs after startup.")
    parser.add_argument("--stop", action="store_true", help="Stop containers without deleting database data.")
    parser.add_argument("--restart", action="store_true", help="Restart the complete project.")
    parser.add_argument("--status", action="store_true", help="Show container state.")
    parser.add_argument("--clean", action="store_true", help="Stop containers and remove generated containers/networks.")
    parser.add_argument("--health-report", action="store_true", help="Show service status, ports, response times, and important URLs.")
    parser.add_argument("--test", action="store_true", help="Run available local validation checks.")
    parser.add_argument("--migrate", action="store_true", help="Apply Phase 4 database migrations when the database-backed core API is available.")
    parser.add_argument("--seed", action="store_true", help="Seed Phase 4 database-backed demo data when available.")
    parser.add_argument("--reset-db", action="store_true", help="Reset Phase 4 database data after explicit confirmation when available.")
    parser.add_argument("--train-models", action="store_true", help="Train Phase 4 ML models when ml-service is available.")
    args = parser.parse_args()

    os.chdir(ROOT)
    use_docker = args.docker or args.mode == "docker"
    if args.docker and args.mode != "docker":
        args.mode = "docker"

    if not use_docker:
        if args.profile == "full":
            fail("Local full profile requires Phase 4 optional services that are not implemented yet. Use --profile minimal.")
        if args.health_report:
            local_health_report()
            return
        if args.test:
            run_local_tests()
            return
        if args.migrate:
            run_core_api_cli("migrate")
            return
        if args.seed:
            run_core_api_cli("seed")
            return
        if args.reset_db:
            try:
                answer = input("Reset local development database? Type 'reset local db' to confirm: ").strip()
            except EOFError:
                print("Reset cancelled.")
                return
            if answer == "reset local db":
                run_core_api_cli("reset", "--yes")
                return
            print("Reset cancelled.")
            return
        if args.train_models:
            train_models()
        if args.status:
            local_status()
            return
        if args.stop:
            stop_local_stack()
            return
        if args.clean:
            stop_local_stack()
            shutil.rmtree(RUNTIME_DIR, ignore_errors=True)
            print("Removed local runtime state.")
            return
        if args.restart:
            stop_local_stack()
        start_local_stack(force_install=False, production_frontend=args.build)
        if args.logs:
            show_local_logs()
        return

    compose = find_compose()

    if args.status:
        status(compose)
        return
    if args.stop:
        stop(compose)
        return
    if args.clean:
        clean(compose)
        return
    if args.restart:
        stop(compose)

    check_environment(compose)
    ensure_env_files()
    compose_up(compose, args.build or args.restart)
    if not poll_health():
        show_logs(compose, follow=False)
        fail("One or more services failed to become healthy.")
    show_summary(mode="docker")
    if args.logs:
        show_logs(compose, follow=True)


if __name__ == "__main__":
    main()
