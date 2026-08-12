# 构建 ROS2 OV-SLAM Docker 镜像

## 设置 / 输入

- 基础 Docker 镜像：`khronos:ros2-jazzy`。
- 生成的 Docker 镜像：`scarf-slam:ros2-ovslam-jazzy`。
- 镜像内构建工作区：`/ros2_ws`。
- 临时构建容器占位符：`<build-container>`。
- 所需源码仓库：
  - `https://github.com/rpng/open_vins.git`
  - `https://github.com/ori-drs/ov_secondary_scarf.git`
- 目标 ROS2 包：
  - `ov_msckf`
  - `ov_secondary_loop_fusion`

## 任务描述

创建一个可复用的 ROS2 Jazzy Docker 镜像，用于运行 ScaRF-SLAM 的 OV-SLAM launch 流程，其中包含 OpenVINS MSCKF 和 OV secondary loop fusion。

## 工作流程概述

1. 从 ROS2 Jazzy 基础镜像启动临时构建容器。

   ```bash
   docker run -dit --name <build-container> khronos:ros2-jazzy bash
   ```

2. 安装所需的 C++ 构建依赖。

   ```bash
   docker exec -u root <build-container> bash -lc \
     'apt-get update &&
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        git libeigen3-dev libboost-all-dev libceres-dev'
   ```

   基础镜像已经包含 ROS2 Jazzy、`colcon`、Eigen、Boost、RViz2 和常用 ROS2 bag 工具。`libceres-dev` 是本次构建中关键缺失依赖。

3. 确保 `/ros2_ws` 对容器运行用户可写。

   ```bash
   docker exec -u root <build-container> bash -lc \
     'chown -R $(id -u):$(id -g) /ros2_ws || true'
   ```

   如果基础镜像中的运行用户名称不同，请显式使用对应用户和用户组。

4. 将 OpenVINS 和 OV secondary loop fusion 克隆到 ROS2 工作区。

   ```bash
   docker exec <build-container> bash -lc \
     'cd /ros2_ws/src &&
      test -d open_vins || git clone https://github.com/rpng/open_vins.git &&
      test -d ov_secondary_scarf || git clone https://github.com/ori-drs/ov_secondary_scarf.git'
   ```

5. 为 ROS2 Jazzy 兼容性修补 OpenVINS 的 ROS2 include。

   在 `/ros2_ws/src/open_vins/ov_msckf/src/ros/ROS2Visualizer.h` 中替换：

   ```text
   image_transport/image_transport.h      -> image_transport/image_transport.hpp
   tf2_geometry_msgs/tf2_geometry_msgs.h  -> tf2_geometry_msgs/tf2_geometry_msgs.hpp
   cv_bridge/cv_bridge.h                  -> cv_bridge/cv_bridge.hpp
   ```

   在 `/ros2_ws/src/open_vins/ov_msckf/src/ros/ROSVisualizerHelper.h` 中替换：

   ```text
   tf2_geometry_msgs/tf2_geometry_msgs.h  -> tf2_geometry_msgs/tf2_geometry_msgs.hpp
   ```

6. 只构建所需包及其依赖。

   ```bash
   docker exec <build-container> bash -lc \
     'cd /ros2_ws &&
      source /opt/ros/jazzy/setup.bash &&
      colcon build --symlink-install \
        --packages-up-to ov_msckf ov_secondary_loop_fusion \
        --parallel-workers 4 \
        --cmake-args -DCMAKE_BUILD_TYPE=Release'
   ```

7. 在镜像中添加便捷 setup 脚本。

   创建 `/ros2_ws/setup_ovslam.bash`：

   ```bash
   #!/usr/bin/env bash
   source /opt/ros/jazzy/setup.bash
   source /ros2_ws/install/setup.bash
   ```

   设置可执行权限：

   ```bash
   docker exec <build-container> bash -lc 'chmod +x /ros2_ws/setup_ovslam.bash'
   ```

8. 在提交镜像前验证包环境。

   ```bash
   docker exec <build-container> bash -lc \
     'source /ros2_ws/setup_ovslam.bash &&
      ros2 pkg prefix ov_msckf &&
      ros2 pkg prefix ov_secondary_loop_fusion &&
      ros2 pkg executables ov_msckf &&
      ros2 pkg executables ov_secondary_loop_fusion'
   ```

9. 将验证通过的容器提交为可复用本地镜像。

   ```bash
   docker commit <build-container> scarf-slam:ros2-ovslam-jazzy
   ```

10. 从全新容器对提交后的镜像做冒烟测试。

   ```bash
   docker run --rm scarf-slam:ros2-ovslam-jazzy bash -lc \
     'source /ros2_ws/setup_ovslam.bash &&
      ros2 pkg prefix ov_msckf &&
      ros2 pkg prefix ov_secondary_loop_fusion &&
      ros2 pkg executables ov_msckf &&
      ros2 pkg executables ov_secondary_loop_fusion'
   ```

## 验证

- `ros2 pkg prefix ov_msckf` 应解析到 `/ros2_ws/install/ov_msckf`。
- `ros2 pkg prefix ov_secondary_loop_fusion` 应解析到 `/ros2_ws/install/ov_secondary_loop_fusion`。
- 期望可执行文件包括：

  ```text
  ov_msckf run_subscribe_msckf
  ov_secondary_loop_fusion loop_fusion_node
  ```

- 已提交的镜像存在：

  ```bash
  docker images --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | grep '^scarf-slam:ros2-ovslam-jazzy '
  ```

## 最终状态

- 可复用本地镜像：

  ```text
  scarf-slam:ros2-ovslam-jazzy
  ```

- 镜像内可复用 setup 脚本：

  ```text
  /ros2_ws/setup_ovslam.bash
  ```

- 该镜像可用于单独的 OV-SLAM 运行流程。

## 失败尝试 / 备注

- 基础镜像 `khronos:ros2-jazzy` 可以检查和播放 ROS2 bag，但默认不包含 `ov_msckf` 或 `ov_secondary_loop_fusion`。
- 如果保留旧的 `.h` ROS2 include 路径，OpenVINS 在 ROS2 Jazzy 上可能构建失败。重新构建前需要应用 `.hpp` include 修补。
- 如果 `apt-get` 因权限失败，请使用 `docker exec -u root` 以 root 身份重新执行安装步骤。

## 占位符实际值

- `<build-container>`：用于构建并提交 `scarf-slam:ros2-ovslam-jazzy` 的临时 Docker 容器。
