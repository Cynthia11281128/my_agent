# Extract an OCI Image Archive into a Usable Rootfs

## Settings / Inputs

This workflow is for a remote Linux server where Docker cannot run containers because the session is already inside a restricted container, but the Docker/OCI image archive must still be used as a runnable software environment.

Use placeholders for machine-specific values:

- `<server>`: SSH target host.
- `<project-root>`: Working directory on the server data disk.
- `<image-archive>`: Docker/OCI image archive file.
- `<oci-layout-dir>`: Temporary extracted OCI layout directory.
- `<rootfs-bundle-dir>`: Final unpacked OCI bundle.
- `<rootfs>`: Final root filesystem directory, normally `<rootfs-bundle-dir>/rootfs`.
- `<env-name>`: Conda environment inside the image, such as `layout`, `sam2`, `oneformer`, or `cropformer`.

## Task Description

Use a Docker/OCI image archive on a restricted remote server without relying on Docker container execution. The intended outcome is an unpacked root filesystem whose Conda environments can be invoked directly, including GPU-enabled PyTorch when the host already exposes NVIDIA devices and driver libraries.

## Workflow Summary

1. SSH to the target server and move to the archive directory.

```bash
ssh <server>
cd <project-root>/docker
```

2. Confirm the complete archive exists and, if split chunks are present, verify that the chunks are only a transfer aid.

```bash
ls -lh <image-archive>
file <image-archive>

sum=0
for f in core-env-chunks/*.part-*; do
  size=$(stat -c %s "$f")
  sum=$((sum + size))
done
full=$(stat -c %s <image-archive>)
echo "chunk_sum_bytes=$sum"
echo "full_size_bytes=$full"
test "$sum" = "$full" && echo "chunks_match_full=yes"
```

3. Install OCI image tools.

```bash
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y skopeo umoci jq
```

4. Ensure large temporary files use the data disk rather than the small system disk. Some versions of `skopeo` use `/var/tmp` directly, so point `/var/tmp` at a data-disk-backed directory.

```bash
mkdir -p <project-root>/var-tmp
rm -rf /var/tmp/oci* /tmp/oci* 2>/dev/null || true
find /var/tmp -mindepth 1 -maxdepth 1 -exec mv -t <project-root>/var-tmp {} + 2>/dev/null || true
rmdir /var/tmp 2>/dev/null || true
ln -s <project-root>/var-tmp /var/tmp
chmod 1777 <project-root>/var-tmp
df -h / <project-root>
```

5. Inspect the image archive without Docker.

```bash
skopeo inspect oci-archive:<image-archive>
```

Record the image tag from `index.json` or the inspect output. In this run the image reference was `layout-reconstruction:core-env`, and the OCI tag used by `umoci` was `core-env`.

6. Extract the compressed OCI archive into an OCI layout directory on the data disk.

```bash
mkdir -p <oci-layout-dir>
tar -xzf <project-root>/docker/<image-archive> -C <oci-layout-dir>
jq . <oci-layout-dir>/index.json
```

7. Unpack the OCI image into a rootfs bundle.

```bash
rm -rf <rootfs-bundle-dir>
umoci unpack --image <oci-layout-dir>:core-env <rootfs-bundle-dir>
```

8. Confirm the bundle and rootfs were created.

```bash
ls -la <rootfs-bundle-dir>
find <rootfs> -maxdepth 2 -type d | head
du -sh <oci-layout-dir> <rootfs-bundle-dir> <project-root>/docker/<image-archive>
```

9. Test direct execution of Python from the unpacked rootfs.

```bash
<rootfs>/opt/conda/bin/python -V
chroot <rootfs> /opt/conda/bin/python -V
```

10. Run a Conda environment from the rootfs without entering Docker. This preserves the image environment while using the current server process namespace and exposed NVIDIA devices.

```bash
ROOTFS=<rootfs>
ENV=<env-name>

PATH="$ROOTFS/opt/conda/envs/$ENV/bin:$ROOTFS/opt/conda/bin:$ROOTFS/usr/local/cuda/bin:$PATH" \
LD_LIBRARY_PATH="$ROOTFS/usr/local/cuda/lib64:$ROOTFS/opt/conda/envs/$ENV/lib:$ROOTFS/opt/conda/lib:/usr/lib/x86_64-linux-gnu:/usr/local/nvidia/lib64:/usr/local/nvidia/lib" \
"$ROOTFS/opt/conda/envs/$ENV/bin/python" your_script.py
```

11. Verify PyTorch and CUDA from each relevant environment.

```bash
ROOTFS=<rootfs>

for envname in layout sam2 oneformer cropformer; do
  py="$ROOTFS/opt/conda/envs/$envname/bin/python"
  echo "==== $envname ===="
  PATH="$ROOTFS/opt/conda/envs/$envname/bin:$ROOTFS/opt/conda/bin:$ROOTFS/usr/local/cuda/bin:$PATH" \
  LD_LIBRARY_PATH="$ROOTFS/usr/local/cuda/lib64:$ROOTFS/opt/conda/envs/$envname/lib:$ROOTFS/opt/conda/lib:/usr/lib/x86_64-linux-gnu:/usr/local/nvidia/lib64:/usr/local/nvidia/lib" \
  "$py" - <<'PY'
import sys
print("python", sys.version.split()[0])
try:
    import torch
    print("torch", torch.__version__)
    print("cuda_available", torch.cuda.is_available())
    print("cuda_version", torch.version.cuda)
    if torch.cuda.is_available():
        print("device", torch.cuda.get_device_name(0))
except Exception as e:
    print("torch_error", type(e).__name__, e)
PY
done
```

## Verification

- `skopeo inspect oci-archive:<image-archive>` successfully read the archive metadata.
- The image digest was available and the image labels showed Ubuntu 22.04, CUDA 12.8, and cuDNN 9.8 metadata.
- `umoci unpack --image <oci-layout-dir>:core-env <rootfs-bundle-dir>` completed successfully.
- `<rootfs>/opt/conda/bin/python -V` and `chroot <rootfs> /opt/conda/bin/python -V` both returned Python versions.
- The following Conda environments were tested successfully with GPU-visible PyTorch:
  - `layout`: Python 3.11.15, torch 2.11.0+cu128, CUDA available, NVIDIA GeForce RTX 4090 D.
  - `sam2`: Python 3.11.15, torch 2.11.0+cu128, CUDA available, NVIDIA GeForce RTX 4090 D.
  - `oneformer`: Python 3.8.20, torch 1.10.1+cu113, CUDA available, NVIDIA GeForce RTX 4090 D.
  - `cropformer`: Python 3.8.20, torch 2.4.1+cu118, CUDA available, NVIDIA GeForce RTX 4090 D.

## Final State

- The image archive was successfully converted into a usable unpacked rootfs bundle.
- Docker container execution was not required for the final working path.
- The final runtime entrypoint is direct invocation of Python from `<rootfs>/opt/conda/envs/<env-name>/bin/python` with `PATH` and `LD_LIBRARY_PATH` set as shown above.
- `<oci-layout-dir>` is an intermediate artifact and can be deleted after confirming the rootfs works.
- `<rootfs-bundle-dir>` is required for future runs.
- The original `<image-archive>` should be kept if the rootfs needs to be regenerated later.

## Failed Attempts / Notes

- Installing Docker and starting `dockerd` succeeded only partially. The default overlay/containerd snapshotter path failed when unpacking/running layers because the restricted outer container did not allow required bind mounts.
- A `vfs` Docker daemon also started, but `docker load` failed with `unshare: operation not permitted`.
- These Docker failures indicate a restricted container environment, not a broken image archive.
- `skopeo` initially failed because `/var/tmp` was on the small system disk. Moving `/var/tmp` to a data-disk-backed directory fixed the space issue.
- Split chunks were not required once the complete archive existed; they were useful only for transfer or size verification.

## Placeholder Values

- `<server>`: `seeta`.
- `<project-root>`: `/root/autodl-tmp/layout_reconstruction`.
- `<image-archive>`: `layout-reconstruction_core-env.tar.gz`.
- `<oci-layout-dir>`: `/root/autodl-tmp/layout_reconstruction/oci-layout`.
- `<rootfs-bundle-dir>`: `/root/autodl-tmp/layout_reconstruction/rootfs-bundle`.
- `<rootfs>`: `/root/autodl-tmp/layout_reconstruction/rootfs-bundle/rootfs`.
- `<env-name>`: one of `layout`, `sam2`, `oneformer`, or `cropformer`.
