# 将 OCI 镜像归档解包为可用 Rootfs

## 设置 / 输入

这个工作流适用于一种远程 Linux 服务器场景：当前会话本身已经运行在受限容器中，Docker 无法正常启动子容器，但仍然需要使用 Docker/OCI 镜像归档中的软件环境。

使用以下占位符表示机器相关值：

- `<server>`：SSH 目标主机。
- `<project-root>`：服务器数据盘上的工作目录。
- `<image-archive>`：Docker/OCI 镜像归档文件。
- `<oci-layout-dir>`：临时解出的 OCI layout 目录。
- `<rootfs-bundle-dir>`：最终解包出的 OCI bundle。
- `<rootfs>`：最终 root filesystem 目录，通常是 `<rootfs-bundle-dir>/rootfs`。
- `<env-name>`：镜像内部的 Conda 环境，例如 `layout`、`sam2`、`oneformer` 或 `cropformer`。

## 任务描述

在受限远程服务器上使用 Docker/OCI 镜像归档，但不依赖 Docker 容器运行能力。目标是得到一个解包后的 root filesystem，并能直接调用其中的 Conda 环境；如果宿主环境已经暴露 NVIDIA 设备和驱动库，则 PyTorch GPU 也应可用。

## 工作流摘要

1. SSH 到目标服务器，并进入镜像归档所在目录。

```bash
ssh <server>
cd <project-root>/docker
```

2. 确认完整归档存在；如果有分片，验证分片只是传输辅助文件。

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

3. 安装 OCI 镜像处理工具。

```bash
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y skopeo umoci jq
```

4. 确保大型临时文件写到数据盘，而不是较小的系统盘。某些版本的 `skopeo` 会直接使用 `/var/tmp`，因此将 `/var/tmp` 指向数据盘目录。

```bash
mkdir -p <project-root>/var-tmp
rm -rf /var/tmp/oci* /tmp/oci* 2>/dev/null || true
find /var/tmp -mindepth 1 -maxdepth 1 -exec mv -t <project-root>/var-tmp {} + 2>/dev/null || true
rmdir /var/tmp 2>/dev/null || true
ln -s <project-root>/var-tmp /var/tmp
chmod 1777 <project-root>/var-tmp
df -h / <project-root>
```

5. 不经过 Docker，直接检查镜像归档元信息。

```bash
skopeo inspect oci-archive:<image-archive>
```

记录 `index.json` 或 inspect 输出中的镜像 tag。本次运行中，镜像引用是 `layout-reconstruction:core-env`，`umoci` 使用的 OCI tag 是 `core-env`。

6. 将压缩的 OCI archive 解到数据盘上的 OCI layout 目录。

```bash
mkdir -p <oci-layout-dir>
tar -xzf <project-root>/docker/<image-archive> -C <oci-layout-dir>
jq . <oci-layout-dir>/index.json
```

7. 将 OCI 镜像解包为 rootfs bundle。

```bash
rm -rf <rootfs-bundle-dir>
umoci unpack --image <oci-layout-dir>:core-env <rootfs-bundle-dir>
```

8. 确认 bundle 和 rootfs 已生成。

```bash
ls -la <rootfs-bundle-dir>
find <rootfs> -maxdepth 2 -type d | head
du -sh <oci-layout-dir> <rootfs-bundle-dir> <project-root>/docker/<image-archive>
```

9. 测试直接运行 rootfs 中的 Python。

```bash
<rootfs>/opt/conda/bin/python -V
chroot <rootfs> /opt/conda/bin/python -V
```

10. 不进入 Docker，直接运行 rootfs 中的 Conda 环境。这样可以复用镜像环境，同时使用当前服务器进程命名空间和已经暴露的 NVIDIA 设备。

```bash
ROOTFS=<rootfs>
ENV=<env-name>

PATH="$ROOTFS/opt/conda/envs/$ENV/bin:$ROOTFS/opt/conda/bin:$ROOTFS/usr/local/cuda/bin:$PATH" \
LD_LIBRARY_PATH="$ROOTFS/usr/local/cuda/lib64:$ROOTFS/opt/conda/envs/$ENV/lib:$ROOTFS/opt/conda/lib:/usr/lib/x86_64-linux-gnu:/usr/local/nvidia/lib64:/usr/local/nvidia/lib" \
"$ROOTFS/opt/conda/envs/$ENV/bin/python" your_script.py
```

11. 逐个验证相关 Conda 环境中的 PyTorch 和 CUDA。

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

## 验证

- `skopeo inspect oci-archive:<image-archive>` 成功读取了归档元信息。
- 镜像 digest 可读取，镜像标签显示 Ubuntu 22.04、CUDA 12.8 和 cuDNN 9.8 相关元数据。
- `umoci unpack --image <oci-layout-dir>:core-env <rootfs-bundle-dir>` 成功完成。
- `<rootfs>/opt/conda/bin/python -V` 和 `chroot <rootfs> /opt/conda/bin/python -V` 都能返回 Python 版本。
- 以下 Conda 环境通过了 GPU 可见的 PyTorch 验证：
  - `layout`：Python 3.11.15，torch 2.11.0+cu128，CUDA 可用，NVIDIA GeForce RTX 4090 D。
  - `sam2`：Python 3.11.15，torch 2.11.0+cu128，CUDA 可用，NVIDIA GeForce RTX 4090 D。
  - `oneformer`：Python 3.8.20，torch 1.10.1+cu113，CUDA 可用，NVIDIA GeForce RTX 4090 D。
  - `cropformer`：Python 3.8.20，torch 2.4.1+cu118，CUDA 可用，NVIDIA GeForce RTX 4090 D。

## 最终状态

- 镜像归档已成功转换为可用的解包 rootfs bundle。
- 最终可用路径不需要 Docker 容器执行能力。
- 最终运行入口是直接调用 `<rootfs>/opt/conda/envs/<env-name>/bin/python`，并按上文设置 `PATH` 和 `LD_LIBRARY_PATH`。
- `<oci-layout-dir>` 是中间产物；确认 rootfs 可用后可以删除。
- `<rootfs-bundle-dir>` 是后续运行所需目录。
- 如果以后需要重新生成 rootfs，应保留原始 `<image-archive>`。

## 失败尝试 / 备注

- 安装 Docker 并启动 `dockerd` 只部分成功。默认 overlay/containerd snapshotter 路径在解包或运行 layer 时失败，因为外层受限容器不允许所需的 bind mount。
- `vfs` Docker daemon 也能启动，但 `docker load` 失败并报 `unshare: operation not permitted`。
- 这些 Docker 失败说明当前环境是受限容器，并不代表镜像归档损坏。
- `skopeo` 起初失败是因为 `/var/tmp` 位于较小的系统盘；将 `/var/tmp` 移到数据盘目录后解决了空间问题。
- 分片文件在完整归档已经存在后不是必需的；它们只适合用于传输或大小校验。

## 占位符实际值

- `<server>`：`seeta`。
- `<project-root>`：`/root/autodl-tmp/layout_reconstruction`。
- `<image-archive>`：`layout-reconstruction_core-env.tar.gz`。
- `<oci-layout-dir>`：`/root/autodl-tmp/layout_reconstruction/oci-layout`。
- `<rootfs-bundle-dir>`：`/root/autodl-tmp/layout_reconstruction/rootfs-bundle`。
- `<rootfs>`：`/root/autodl-tmp/layout_reconstruction/rootfs-bundle/rootfs`。
- `<env-name>`：`layout`、`sam2`、`oneformer` 或 `cropformer`。
