# Run R05 OV-SLAM With The ROS2 Image

## Settings / Inputs

- `<project-root>`: ScaRF-SLAM repository containing `launch/run_ov_slam.launch.py`, `config/open_vins`, `config/ov_secondary`, and `scripts/dataset_utils/image_conversion_node.py`.
- `<dataset-root>`: dataset directory that already contains the required R05 input data.
- Required Docker image: `scarf-slam:ros2-ovslam-jazzy`.
- Main output folder: `<dataset-root>/r05/ov_slam_ros2_image`.
- Playback rate: `0.25`.
- Run headless with `rviz_enable:=false`.

Required input data must already exist before starting:

```text
<dataset-root>/r05/r05_bag/metadata.yaml
<dataset-root>/r05/r05_bag/r05_bag_0.mcap
<dataset-root>/r05/r05_gt/poses_gt.txt
```

Optional evaluation assets:

```text
<dataset-root>/r05/r05_gt/poses_gt.csv
<dataset-root>/r05/r05_gt/cloud_gt.pcd
<dataset-root>/r05/r05_gt/cloud_gt_fov/
```

## Task Description

Use an already-built ROS2 OV-SLAM Docker image to process an existing R05 ROS2 MCAP bag, save the generated OV-SLAM output bag and pose graph, extract camera poses to TUM-style text, and compare the result with ground truth and the earlier ROS1-converted-bag route.

## Workflow Summary

1. Verify that the input bag is readable and has the expected ROS2 topics.

   ```bash
   docker run --rm -v <dataset-root>:/data:ro scarf-slam:ros2-ovslam-jazzy bash -lc \
     'source /ros2_ws/setup_ovslam.bash &&
      ros2 bag info /data/r05/r05_bag'
   ```

   Expected input topics:

   ```text
   /insta/cam0/image_raw/compressed  sensor_msgs/msg/CompressedImage
   /insta/imu/data_raw               sensor_msgs/msg/Imu
   /insta/poses_gt                   nav_msgs/msg/Path
   ```

2. Run R05 through the native ROS2 OV-SLAM launch.

   ```bash
   docker run --rm --name ros2_r05_ovslam --net=host \
     --user $(id -u):$(id -g) \
     -e HOME=/tmp \
     -v <project-root>:/ScaRF-SLAM:ro \
     -v <dataset-root>:/data \
     scarf-slam:ros2-ovslam-jazzy bash -lc \
       'source /ros2_ws/setup_ovslam.bash &&
        cd /ScaRF-SLAM &&
        ros2 launch launch/run_ov_slam.launch.py \
          output_path:=/data/r05/ov_slam_ros2_image \
          bag:=/data/r05/r05_bag \
          bag_rate:=0.25 \
          rviz_enable:=false'
   ```

   Let playback finish. Wait until the loop-fusion node logs:

   ```text
   auto-saved pose graph and closed bag writer after 5s idle with no pending optimization
   ```

   After that message, interrupting the launch is acceptable if the node does not exit by itself.

3. Inspect the generated OV-SLAM output bag.

   ```bash
   docker run --rm -v <dataset-root>:/data:ro scarf-slam:ros2-ovslam-jazzy bash -lc \
     'source /ros2_ws/setup_ovslam.bash &&
      ros2 bag info /data/r05/ov_slam_ros2_image/ov_slam/ov_slam_bag'
   ```

   Expected output topics:

   ```text
   /ov_slam/image/compressed
   /ov_slam/odometry
   /ov_slam/trajectory
   /ov_slam/trajectory_final
   ```

4. Extract OV-SLAM poses to TUM-style text.

   Use `rosbags` from the Docker image to read:

   ```text
   /ov_slam/odometry
   /ov_slam/trajectory
   /ov_slam/trajectory_final
   ```

   Write text files with columns:

   ```text
   # timestamp tx ty tz qx qy qz qw
   ```

   Recommended output files:

   ```text
   <dataset-root>/r05/ov_slam_ros2_image/poses/ov_slam_odometry.txt
   <dataset-root>/r05/ov_slam_ros2_image/poses/ov_slam_trajectory_last.txt
   <dataset-root>/r05/ov_slam_ros2_image/poses/ov_slam_trajectory_final.txt
   ```

   The loop-fusion node also writes the final trajectory directly:

   ```text
   <dataset-root>/r05/ov_slam_ros2_image/ov_slam/trajectory_final.txt
   ```

5. Evaluate against R05 ground truth with Sim3 ATE.

   Use `<dataset-root>/r05/r05_gt/poses_gt.txt` as ground truth. Match timestamps within `0.01s`, estimate Sim3 alignment from trajectory translations, and compute translation ATE RMSE, mean, median, p95, and max.

   For a comparison with the earlier ROS1 route, convert ROS1 IMU/body pose outputs to camera positions before evaluating:

   ```text
   p_C_in_G = p_I_in_G + R_GI * p_C_in_I
   ```

   Use `T_cam_imu` from `<project-root>/config/open_vins/kalibr_imucam_chain.yaml`.

## Verification

- Input `ros2 bag info` should report an MCAP ROS2 bag with camera, IMU, and GT path topics.
- The full run should create:

  ```text
  <dataset-root>/r05/ov_slam_ros2_image/ov_slam/ov_slam_bag/
  <dataset-root>/r05/ov_slam_ros2_image/ov_slam/pose_graph/
  <dataset-root>/r05/ov_slam_ros2_image/ov_slam/trajectory_final.txt
  ```

- Expected generated output bag topic counts for R05:

  ```text
  /ov_slam/image/compressed       1486
  /ov_slam/odometry               1486
  /ov_slam/trajectory             1486
  /ov_slam/trajectory_final       1
  ```

- Expected extracted text counts for R05:

  ```text
  ov_slam_odometry.txt            1486 poses
  ov_slam_trajectory_last.txt     1486 poses
  ov_slam_trajectory_final.txt    1486 poses
  ```

- Sim3 ATE to R05 ground truth with `0.01s` timestamp tolerance from this run:

  | Output | Matched poses | ATE RMSE |
  |---|---:|---:|
  | ROS1 `ov_msckf`, IMU converted to camera | 2539 | 0.171 m |
  | ROS1 `ov_secondary`, IMU converted to camera | 2535 | 0.223 m |
  | ROS2 `/ov_slam/odometry` | 1486 | 0.0838 m |
  | ROS2 `/ov_slam/trajectory_last` | 1486 | 0.0255 m |
  | ROS2 `/ov_slam/trajectory_final` | 1486 | 0.0397 m |

## Final State

- Native ROS2 OV-SLAM output folder:

  ```text
  <dataset-root>/r05/ov_slam_ros2_image
  ```

- Main final pose file:

  ```text
  <dataset-root>/r05/ov_slam_ros2_image/ov_slam/trajectory_final.txt
  ```

- Extracted final pose file:

  ```text
  <dataset-root>/r05/ov_slam_ros2_image/poses/ov_slam_trajectory_final.txt
  ```

- Best measured trajectory in this run:

  ```text
  <dataset-root>/r05/ov_slam_ros2_image/poses/ov_slam_trajectory_last.txt
  ```

- The native ROS2 route reproduces the paper-level R05 OV-SLAM result much more closely than the ROS1-converted-bag route.

## Failed Attempts / Notes

- The ROS1-converted-bag route produced much worse R05 Sim3 ATE than the native ROS2 route.
- ROS1 pose text files are IMU/body pose streams; the ROS2 `/ov_slam/*` outputs are camera keyframe pose streams, so compare them carefully.
- The loop-fusion process may require manual interruption after autosave. Only interrupt after the log confirms the pose graph was saved and the bag writer was closed.

## Placeholder Values

- `<project-root>`: local ScaRF-SLAM repository root; personal path prefix redacted.
- `<dataset-root>`: local directory containing the already-available R05 input data; personal path prefix redacted.
