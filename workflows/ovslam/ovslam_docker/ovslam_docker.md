# Build A ROS2 OV-SLAM Docker Image

## Settings / Inputs

- Base Docker image: `khronos:ros2-jazzy`.
- Generated Docker image: `scarf-slam:ros2-ovslam-jazzy`.
- Build workspace inside the image: `/ros2_ws`.
- Temporary build container placeholder: `<build-container>`.
- Required source repositories:
  - `https://github.com/rpng/open_vins.git`
  - `https://github.com/ori-drs/ov_secondary_scarf.git`
- Target ROS2 packages:
  - `ov_msckf`
  - `ov_secondary_loop_fusion`

## Task Description

Create a reusable ROS2 Jazzy Docker image that can run ScaRF-SLAM's OV-SLAM launch path with OpenVINS MSCKF and OV secondary loop fusion.

## Workflow Summary

1. Start a temporary build container from the ROS2 Jazzy base image.

   ```bash
   docker run -dit --name <build-container> khronos:ros2-jazzy bash
   ```

2. Install the required C++ build dependencies.

   ```bash
   docker exec -u root <build-container> bash -lc \
     'apt-get update &&
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        git libeigen3-dev libboost-all-dev libceres-dev'
   ```

   The base image already includes ROS2 Jazzy, `colcon`, Eigen, Boost, RViz2, and common ROS2 bag tools. `libceres-dev` is the important missing package for this build.

3. Make sure `/ros2_ws` is writable by the container runtime user.

   ```bash
   docker exec -u root <build-container> bash -lc \
     'chown -R $(id -u):$(id -g) /ros2_ws || true'
   ```

   If the runtime user is named differently in your base image, use that user and group explicitly.

4. Clone OpenVINS and OV secondary loop fusion into the ROS2 workspace.

   ```bash
   docker exec <build-container> bash -lc \
     'cd /ros2_ws/src &&
      test -d open_vins || git clone https://github.com/rpng/open_vins.git &&
      test -d ov_secondary_scarf || git clone https://github.com/ori-drs/ov_secondary_scarf.git'
   ```

5. Patch OpenVINS ROS2 includes for ROS2 Jazzy compatibility.

   In `/ros2_ws/src/open_vins/ov_msckf/src/ros/ROS2Visualizer.h`, replace:

   ```text
   image_transport/image_transport.h      -> image_transport/image_transport.hpp
   tf2_geometry_msgs/tf2_geometry_msgs.h  -> tf2_geometry_msgs/tf2_geometry_msgs.hpp
   cv_bridge/cv_bridge.h                  -> cv_bridge/cv_bridge.hpp
   ```

   In `/ros2_ws/src/open_vins/ov_msckf/src/ros/ROSVisualizerHelper.h`, replace:

   ```text
   tf2_geometry_msgs/tf2_geometry_msgs.h  -> tf2_geometry_msgs/tf2_geometry_msgs.hpp
   ```

6. Build only the required packages and dependencies.

   ```bash
   docker exec <build-container> bash -lc \
     'cd /ros2_ws &&
      source /opt/ros/jazzy/setup.bash &&
      colcon build --symlink-install \
        --packages-up-to ov_msckf ov_secondary_loop_fusion \
        --parallel-workers 4 \
        --cmake-args -DCMAKE_BUILD_TYPE=Release'
   ```

7. Add a convenience setup script inside the image.

   Create `/ros2_ws/setup_ovslam.bash`:

   ```bash
   #!/usr/bin/env bash
   source /opt/ros/jazzy/setup.bash
   source /ros2_ws/install/setup.bash
   ```

   Make it executable:

   ```bash
   docker exec <build-container> bash -lc 'chmod +x /ros2_ws/setup_ovslam.bash'
   ```

8. Verify the package environment before committing.

   ```bash
   docker exec <build-container> bash -lc \
     'source /ros2_ws/setup_ovslam.bash &&
      ros2 pkg prefix ov_msckf &&
      ros2 pkg prefix ov_secondary_loop_fusion &&
      ros2 pkg executables ov_msckf &&
      ros2 pkg executables ov_secondary_loop_fusion'
   ```

9. Commit the verified container as a reusable local image.

   ```bash
   docker commit <build-container> scarf-slam:ros2-ovslam-jazzy
   ```

10. Smoke-test the committed image from a fresh container.

   ```bash
   docker run --rm scarf-slam:ros2-ovslam-jazzy bash -lc \
     'source /ros2_ws/setup_ovslam.bash &&
      ros2 pkg prefix ov_msckf &&
      ros2 pkg prefix ov_secondary_loop_fusion &&
      ros2 pkg executables ov_msckf &&
      ros2 pkg executables ov_secondary_loop_fusion'
   ```

## Verification

- `ros2 pkg prefix ov_msckf` resolves to `/ros2_ws/install/ov_msckf`.
- `ros2 pkg prefix ov_secondary_loop_fusion` resolves to `/ros2_ws/install/ov_secondary_loop_fusion`.
- Expected executables include:

  ```text
  ov_msckf run_subscribe_msckf
  ov_secondary_loop_fusion loop_fusion_node
  ```

- The committed image exists:

  ```bash
  docker images --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}' | grep '^scarf-slam:ros2-ovslam-jazzy '
  ```

## Final State

- Reusable local image:

  ```text
  scarf-slam:ros2-ovslam-jazzy
  ```

- Reusable setup helper inside the image:

  ```text
  /ros2_ws/setup_ovslam.bash
  ```

- The image is ready for the separate OV-SLAM run workflow.

## Failed Attempts / Notes

- The base `khronos:ros2-jazzy` image can inspect and play ROS2 bags, but it does not include `ov_msckf` or `ov_secondary_loop_fusion` by default.
- The OpenVINS build can fail on ROS2 Jazzy if old `.h` ROS2 include paths are left unchanged. Apply the `.hpp` include patch before rebuilding.
- If `apt-get` fails with permission errors, rerun the install step as root with `docker exec -u root`.

## Placeholder Values

- `<build-container>`: temporary Docker container used to build and commit `scarf-slam:ros2-ovslam-jazzy`.
