"""Linux server deployment. No Git credentials or bot secrets leave the server."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout


def inspect_container():
    result = subprocess.run(["docker", "inspect", "notorious-bot"], text=True, capture_output=True)
    if result.returncode:
        if "No such" in result.stderr:
            return None
        raise RuntimeError("Cannot inspect Docker container; check Docker service and permissions")
    return json.loads(result.stdout)[0]


def volume_name(previous, target, default):
    if previous:
        mount = next((m for m in previous["Mounts"] if m["Destination"] == target), None)
        if mount:
            if mount["Type"] != "volume":
                raise RuntimeError(f"Expected named volume for {target}; migrate this mount explicitly first")
            return mount["Name"]
    return default


def compose_config(app_dir, image, data_volume, cache_volume):
    return {
        "services": {"notorious-bot": {
            "image": image, "container_name": "notorious-bot", "restart": "unless-stopped",
            "network_mode": "host", "stop_grace_period": "30s",
            "env_file": [str(app_dir / ".env")],
            "environment": {
                "YTDLP_COOKIES_PATH": "/app/cookies.txt", "QUEUE_STATE_PATH": "/app/data/queues.json",
                "DAILY_VICTIMS_STATE_PATH": "/app/data/daily_victims.json",
                "PLAYLISTS_DB_PATH": "/app/data/playlists.sqlite3", "PYTHONUNBUFFERED": "1",
            },
            "volumes": ["data:/app/data", "cache:/tmp/yt-dlp", {
                "type": "bind", "source": str(app_dir / "cookies.txt"), "target": "/app/cookies.txt",
                "bind": {"create_host_path": False},
            }],
            "healthcheck": {
                "test": ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=5)"],
                "interval": "10s", "timeout": "6s", "retries": 6, "start_period": "30s",
            },
        }},
        "volumes": {
            "data": {"name": data_volume, "external": True},
            "cache": {"name": cache_volume, "external": True},
        },
    }


def wait_healthy(expected_image, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        container = inspect_container()
        if container and container["Image"] == expected_image:
            state = container["State"]
            if state.get("Status") == "running" and state.get("Health", {}).get("Status") == "healthy":
                return
        time.sleep(3)
    raise RuntimeError("New container did not become healthy within 180 seconds")


def deploy(app_dir, sha):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Expected full 40-character commit SHA")
    app_dir = Path(app_dir).resolve()
    release_dir = app_dir / "releases" / sha
    for name in (".env", "cookies.txt"):
        if not (app_dir / name).is_file():
            raise RuntimeError(f"Missing server file: {app_dir / name}")
    run("docker", "compose", "version")
    image_archive = release_dir / "bot-image.tar.gz"
    expected = (release_dir / "bot-image.tar.gz.sha256").read_text().split()[0]
    digest = hashlib.sha256()
    with image_archive.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != expected:
        raise RuntimeError("Image archive checksum mismatch")
    previous = inspect_container()
    project = ((previous or {}).get("Config", {}).get("Labels") or {}).get(
        "com.docker.compose.project", "discord-bot")
    data_volume = volume_name(previous, "/app/data", f"{project}_bot_data")
    cache_volume = volume_name(previous, "/tmp/yt-dlp", f"{project}_yt_cache")
    run("docker", "load", "-i", str(image_archive))
    image = f"discord-bot:{sha}"
    metadata = json.loads(run("docker", "image", "inspect", image))[0]
    if (metadata["Config"].get("Labels") or {}).get("org.opencontainers.image.revision") != sha:
        raise RuntimeError("Image revision does not match requested commit")
    # Adopt old Compose volumes without changing their original ownership labels.
    # Docker volume create is idempotent for an existing named volume.
    for volume in (data_volume, cache_volume):
        run("docker", "volume", "create", volume)
    compose = release_dir / "compose.json"
    config = compose_config(app_dir, image, data_volume, cache_volume)
    compose.write_text(json.dumps(config, indent=2))
    command = ("docker", "compose", "-p", project, "-f", str(compose))
    run(*command, "config", "--quiet")
    try:
        run(*command, "up", "-d", "--no-build", "--pull", "never", "--force-recreate")
        wait_healthy(metadata["Id"])
    except Exception:
        if previous:
            # Keep the old image addressable even if its original tag was overwritten.
            rollback_image = f"discord-bot:rollback-{sha}"
            run("docker", "tag", previous["Image"], rollback_image)
            config["services"]["notorious-bot"]["image"] = rollback_image
            rollback = release_dir / "rollback.json"
            rollback.write_text(json.dumps(config, indent=2))
            run("docker", "compose", "-p", project, "-f", str(rollback),
                "up", "-d", "--no-build", "--pull", "never", "--force-recreate")
            wait_healthy(previous["Image"])
            print("Deployment failed; previous image restored", flush=True)
        else:
            run(*command, "stop")
        raise
    marker = app_dir / "deployed-revision.tmp"
    marker.write_text(sha + "\n")
    marker.replace(app_dir / "deployed-revision")
    image_archive.unlink()
    (release_dir / "bot-image.tar.gz.sha256").unlink()
    print(f"Deployed and healthy: {sha}", flush=True)


if __name__ == "__main__":
    import fcntl

    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", required=True)
    parser.add_argument("--sha", required=True)
    args = parser.parse_args()
    # Also prevents concurrent manual runs on the host.
    with (Path(args.app_dir) / ".deploy.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            deploy(args.app_dir, args.sha)
        except Exception as error:
            # Do not dump subprocess output: docker/compose output can include environment values.
            print(f"Deployment failed: {type(error).__name__}: {error}", flush=True)
            raise SystemExit(1)
