# Docker 镜像导出为 tar.zst 流程

## 设置 / 输入

- 仓库根目录：`<project-root>`
- Dockerfile 路径：`<dockerfile-path>`
- Docker 镜像 tag：`<image-tag>`
- 可选 build wrapper：`<build-script>`
- 可选 run wrapper：`<run-script>`
- 可选 smoke-test wrapper：`<test-script>`
- 外部权重目录：`<weights-root>`
- 外部数据目录：`<data-root>`
- 打包目录：`<pack-dir>`
- 导出压缩包：`<archive-name>.tar.zst`
- 导出 checksum：`<archive-name>.tar.zst.sha256`

目标主机需要具备：

- Linux x86_64。
- 如果镜像需要 GPU，host 需要 NVIDIA GPU 和可用驱动。
- Docker daemon；如果是 GPU 镜像，还需要 NVIDIA container runtime。
- 用于 `.tar.zst` 导出和完整性检查的 `zstd`。
- 足够的磁盘空间，用于 build context、Docker layer、未压缩的 `docker save` 流、压缩包和临时 cache。

## 任务描述

为项目环境创建可复现的 Docker 镜像，验证该镜像能够通过必要的本地运行检查，并将镜像导出为带 checksum 的 `.tar.zst` 压缩包。这个 workflow 到本地打包和 archive 验证为止。

## 流程总结

1. 确定环境边界。
   - 将 runtime 依赖、编译器、Python/conda 环境，以及 build 时需要的项目源码放进 image。
   - 将体积大或经常变化的内容保留在 image 外：dataset、checkpoint、raw capture、生成输出、实验日志和 cache。
   - 如果依赖栈互不兼容，在一个 image 内保留多个环境，而不是强行合并成一个 Python 环境。

2. 创建或检查 Dockerfile。
   - 根据运行需求选择基础镜像，例如 GPU workload 使用带 CUDA 的 NVIDIA 镜像。
   - 安装 OS build/runtime 包、包管理器和语言 runtime。
   - 必要时将每套依赖安装到独立环境。
   - 安装后清理 package cache，减小最终 image 体积。
   - 显式设置 non-interactive 和 cache 相关环境变量。

3. 从干净 context 构建。
   - 优先使用 build wrapper 创建临时 build context，不要直接在完整 working tree 上执行 `docker build`。
   - 排除机器相关或体积大的内容：

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

   - 构建 image：

```bash
cd <project-root>
bash <build-script> --tag <image-tag>
```

   - 如果没有 build wrapper，使用：

```bash
cd <project-root>
docker build -f <dockerfile-path> -t <image-tag> .
```

4. 创建或使用 run wrapper。
   - 用 wrapper 统一 `docker run` 参数，避免用户手动复现所有 runtime flag。
   - 对于 GPU workload，包含 GPU 访问和足够的 shared memory：

```text
--gpus all
--ipc=host
--shm-size=<shared-memory-size>
```

   - 挂载 project root、外部权重、外部数据和可选 cache 目录。
   - 当 bind mount 需要保持 host 用户可写时，使用 host UID/GID 运行。
   - 设置常见 ML stack 需要的 cache/user 变量：

```text
HOME
USER
LOGNAME
HF_HOME
TORCH_HOME
XDG_CACHE_HOME
```

   - 通过 wrapper 启动 shell 或命令：

```bash
cd <project-root>
bash <run-script> --image <image-tag>
```

5. 准备外部 artifact。
   - 将 checkpoint 放在 `<weights-root>`。
   - 将 dataset 放在 `<data-root>`。
   - 重建项目内 symlink 或 config value，保证容器内必需路径可以解析。
   - 不要把 image build 成功等同于 weights 或 datasets 已可用。

6. 在本地验证 image。
   - smoke test 应检查：
     - Docker CLI 和 daemon 可用
     - 需要 GPU 时，NVIDIA runtime 和 `nvidia-smi` 可用
     - image 存在
     - 需要 GPU 时，container 可以看到 GPU
     - 每个 runtime 环境的 imports 通过
     - 关键命令行入口可以解析 `--help`
     - 必需的外部权重或 symlink 可以解析

```bash
cd <project-root>
bash <test-script> --image <image-tag>
```

7. 在本地导出已验证的 image。
   - 将本地打包和后续分发或部署工作分开。
   - 使用专门的打包目录：

```bash
mkdir -p <pack-dir>
docker image inspect <image-tag>
docker save <image-tag> \
  | zstd -T0 -19 \
  -o <pack-dir>/<archive-name>.tar.zst
sha256sum <pack-dir>/<archive-name>.tar.zst \
  > <pack-dir>/<archive-name>.tar.zst.sha256
```

8. 验证导出的 archive。

```bash
cd <pack-dir>
sha256sum -c <archive-name>.tar.zst.sha256
zstd -t <archive-name>.tar.zst
```

## 验证

- image build 完成，并且 `docker image inspect <image-tag>` 成功。
- local smoke test 对所有必需 runtime 环境通过。
- 导出 archive 通过 checksum 验证：

```bash
sha256sum -c <archive-name>.tar.zst.sha256
```

- 导出 archive 通过解压完整性验证：

```bash
zstd -t <archive-name>.tar.zst
```

## 最终状态

- 项目拥有 tag 为 `<image-tag>` 的 Docker image。
- 本地已打包的 image archive 是 `<archive-name>.tar.zst`。
- checksum 文件是 `<archive-name>.tar.zst.sha256`。
- 外部 weights、data、raw input 和 output 仍保留在 image 外部。
- archive 和 checksum 已在本地验证。

## 失败尝试 / 备注

- 不要为了简化 Dockerfile，把互不兼容的依赖栈合并到一个 runtime 环境。
- 默认不要将 dataset 或 checkpoint bake 进 image；这会让 rebuild 和 archive 更大，也更难复用。
- 当 repo 包含 data、output、log 或 cache 目录时，不要直接把未过滤的 repository root 作为 build context。
- 在 `sha256sum -c` 和 `zstd -t` 都通过前，不要称本地 package 已完成。
- 高压缩等级 `zstd -T0 -19` 可能消耗较多时间和内存。当速度比 archive 体积更重要时，应选择较低压缩等级。
- 在另一台机器上加载 archive 不属于这个打包 workflow。

## 占位符实际值

- `<project-root>`：被打包项目的根目录
- `<dockerfile-path>`：用于构建 image 的 Dockerfile 路径
- `<image-tag>`：构建出来的 Docker image tag
- `<build-script>`：项目内用于构建 image 的脚本，如果有
- `<run-script>`：项目内用于启动 container 的脚本，如果有
- `<test-script>`：项目内用于测试 image 的 smoke-test 脚本，如果有
- `<weights-root>`：存放模型权重或 checkpoint 的外部目录
- `<data-root>`：存放 dataset 或 repo-ready input 的外部目录
- `<pack-dir>`：存放导出 archive 和 checksum 的本地目录
- `<archive-name>`：导出 image archive 的基础文件名
- `<shared-memory-size>`：根据 workload 选择的 Docker shared memory 大小
