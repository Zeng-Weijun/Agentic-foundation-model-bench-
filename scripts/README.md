# Scripts

This directory is reserved for lightweight, GitHub-tracked runner wrappers and deployment utilities.

The current local workspace still contains historical `run_*.sh` launchers at the repository root. Before promoting any of them into this directory, audit whether the script is:

- a stable benchmark adapter,
- a legacy launcher,
- a shared-disk-only operational script,
- or a one-off historical runner.

Rootless workers should wrap benchmark adapters rather than treating existing `run_*.sh` files as worker infrastructure.
