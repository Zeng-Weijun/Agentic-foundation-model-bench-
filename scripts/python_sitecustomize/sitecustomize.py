"""Worker-only docker-py compatibility hooks for benchmark wrappers."""

from __future__ import annotations

import os


docker_api_version = os.environ.get("DOCKER_PY_API_VERSION")

docker_shim_dir = os.environ.get("TB21_DOCKER_SHIM_DIR")

if docker_shim_dir:
    path = os.environ.get("PATH", "")
    path_parts = [part for part in path.split(os.pathsep) if part]
    if docker_shim_dir not in path_parts:
        os.environ["PATH"] = docker_shim_dir + (os.pathsep + path if path else "")

if docker_api_version:
    try:
        import docker

        original_from_env = docker.client.DockerClient.from_env.__func__

        def from_env_with_fixed_version(cls, **kwargs):
            kwargs.setdefault("version", docker_api_version)
            return original_from_env(cls, **kwargs)

        docker.client.DockerClient.from_env = classmethod(from_env_with_fixed_version)
        docker.from_env = docker.client.DockerClient.from_env
    except Exception:
        # sitecustomize must not break Python commands that do not import docker-py.
        pass
