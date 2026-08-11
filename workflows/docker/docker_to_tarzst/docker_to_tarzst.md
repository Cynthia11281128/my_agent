# Docker Image to tar.zst Workflow

## Settings / Inputs

- Repository root: `<project-root>`
- Dockerfile path: `<dockerfile-path>`
- Docker image tag: `<image-tag>`
- Optional build wrapper: `<build-script>`
- Optional run wrapper: `<run-script>`
- Optional smoke-test wrapper: `<test-script>`
- External weights root: `<weights-root>`
- External data root: `<data-root>`
- Package directory: `<pack-dir>`
- Export archive: `<archive-name>.tar.zst`
- Export checksum: `<archive-name>.tar.zst.sha256`

Required host capabilities:

- Linux x86_64 host.
- NVIDIA GPU and a working host driver when the image needs GPU access.
- Docker daemon and, for GPU images, NVIDIA container runtime.
- `zstd` for `.tar.zst` export and integrity checks.
- Enough disk for the build context, Docker layers, uncompressed `docker save` stream, compressed archive, and temporary caches.

## Task Description

Create a reproducible Docker image for a project environment, validate that the image can run the required local runtime checks, and export it as a compressed `.tar.zst` archive with a checksum. This workflow stops after local packaging and archive verification.

## Workflow Summary

1. Decide the environment boundary.
   - Put runtime dependencies, compilers, Python/conda environments, and project source needed at build time inside the image.
   - Keep large or frequently changing artifacts outside the image: datasets, checkpoints, raw captures, generated outputs, experiment logs, and caches.
   - If dependency stacks are incompatible, keep multiple environments inside one image instead of forcing a single Python environment.

2. Create or review the Dockerfile.
   - Use a base image that matches the runtime requirement, such as a CUDA-enabled NVIDIA image for GPU workloads.
   - Install OS build/runtime packages, the package manager, and language runtimes.
   - Install each dependency stack in an isolated environment when needed.
   - Clean package caches after installation to reduce final image size.
   - Set non-interactive and cache-related environment variables explicitly.

3. Build from a clean context.
   - Prefer a build wrapper that creates a temporary build context instead of running `docker build` on the full working tree.
   - Exclude machine-specific or bulky content:

```text
.git/
data/
raw_data/
outputs/
logs/
cache/
**/__pycache__/
**/*.pyc
```

   - Build the image:

```bash
cd <project-root>
bash <build-script> --tag <image-tag>
```

   - If no build wrapper exists, use:

```bash
cd <project-root>
docker build -f <dockerfile-path> -t <image-tag> .
```

4. Create or use a run wrapper.
   - Wrap `docker run` so users do not have to reproduce all runtime flags manually.
   - For GPU workloads, include GPU access and enough shared memory:

```text
--gpus all
--ipc=host
--shm-size=<shared-memory-size>
```

   - Mount the project root, external weights, external data, and optional cache directories.
   - Run with host UID/GID when bind mounts should remain writable by the host user.
   - Set cache/user variables that common ML stacks expect:

```text
HOME
USER
LOGNAME
HF_HOME
TORCH_HOME
XDG_CACHE_HOME
```

   - Start a shell or command through the wrapper:

```bash
cd <project-root>
bash <run-script> --image <image-tag>
```

5. Prepare external artifacts.
   - Place checkpoints under `<weights-root>`.
   - Place datasets under `<data-root>`.
   - Recreate project-local symlinks or config values so required paths resolve inside the container.
   - Do not treat successful image build as proof that weights or datasets are available.

6. Validate the image locally.
   - Run a smoke test that checks:
     - Docker CLI and daemon availability
     - NVIDIA runtime and `nvidia-smi` when GPU is required
     - image existence
     - container GPU visibility when GPU is required
     - imports for every runtime environment
     - key command-line entrypoints parse `--help`
     - required external weights or symlinks resolve

```bash
cd <project-root>
bash <test-script> --image <image-tag>
```

7. Export the validated image locally.
   - Keep packaging separate from any later distribution or deployment work.
   - Use a dedicated package directory:

```bash
mkdir -p <pack-dir>
docker image inspect <image-tag>
docker save <image-tag> \
  | zstd -T0 -19 \
  -o <pack-dir>/<archive-name>.tar.zst
sha256sum <pack-dir>/<archive-name>.tar.zst \
  > <pack-dir>/<archive-name>.tar.zst.sha256
```

8. Verify the exported archive.

```bash
cd <pack-dir>
sha256sum -c <archive-name>.tar.zst.sha256
zstd -t <archive-name>.tar.zst
```

## Verification

- Image build completed and `docker image inspect <image-tag>` succeeded.
- Local smoke test passed for all required runtime environments.
- Export archive passed checksum verification:

```bash
sha256sum -c <archive-name>.tar.zst.sha256
```

- Export archive passed decompression integrity verification:

```bash
zstd -t <archive-name>.tar.zst
```

## Final State

- The project has a Docker image tagged as `<image-tag>`.
- The locally packaged image archive is `<archive-name>.tar.zst`.
- The checksum file is `<archive-name>.tar.zst.sha256`.
- External weights, data, raw inputs, and outputs remain outside the image.
- The archive and checksum have been verified locally.

## Failed Attempts / Notes

- Do not merge incompatible dependency stacks into one runtime environment just to simplify the Dockerfile.
- Do not bake datasets or checkpoints into the image by default; it makes rebuilds and archives larger and less reusable.
- Do not use an unfiltered repository root as the build context when the repo contains data, outputs, logs, or cache directories.
- Do not call a package complete until both `sha256sum -c` and `zstd -t` pass.
- High-compression `zstd -T0 -19` can take meaningful time and memory. Use a lower compression level when speed matters more than archive size.
- Loading the archive on another machine is outside this packaging workflow.

## Placeholder Values

- `<project-root>`: root directory of the project being packaged
- `<dockerfile-path>`: path to the Dockerfile used for the image
- `<image-tag>`: Docker tag for the built image
- `<build-script>`: project-specific script that builds the image, if available
- `<run-script>`: project-specific script that starts the container, if available
- `<test-script>`: project-specific image smoke-test script, if available
- `<weights-root>`: external directory containing model weights or checkpoints
- `<data-root>`: external directory containing datasets or repo-ready inputs
- `<pack-dir>`: local directory that stores the exported archive and checksum
- `<archive-name>`: base name of the exported image archive
- `<shared-memory-size>`: Docker shared memory size chosen for the workload
