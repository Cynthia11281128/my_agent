# 使用 ROS2 镜像运行 R05 OV-SLAM

## 设置 / 输入

- `<project-root>`：ScaRF-SLAM 仓库，包含 `launch/run_ov_slam.launch.py`、`config/open_vins`、`config/ov_secondary` 和 `scripts/dataset_utils/image_conversion_node.py`。
- `<dataset-root>`：已经包含所需 R05 输入数据的数据集目录。
- 所需 Docker 镜像：`scarf-slam:ros2-ovslam-jazzy`。
- 主要输出目录：`<dataset-root>/r05/ov_slam_ros2_image`。
- 播放速率：`0.25`。
- 无界面运行，设置 `rviz_enable:=false`。

开始前必须已经存在以下输入数据：

```text
<dataset-root>/r05/r05_bag/metadata.yaml
<dataset-root>/r05/r05_bag/r05_bag_0.mcap
<dataset-root>/r05/r05_gt/poses_gt.txt
```

可选评估数据：

```text
<dataset-root>/r05/r05_gt/poses_gt.csv
<dataset-root>/r05/r05_gt/cloud_gt.pcd
<dataset-root>/r05/r05_gt/cloud_gt_fov/
```

## 任务描述

使用已经构建好的 ROS2 OV-SLAM Docker 镜像处理现有 R05 ROS2 MCAP bag，保存生成的 OV-SLAM 输出 bag 和 pose graph，将相机位姿导出为 TUM 风格文本，并与真值和之前的 ROS1 转换 bag 路线对比。

## 工作流程概述

1. 验证输入 bag 可读取，并且包含期望的 ROS2 topic。

   ```bash
   docker run --rm -v <dataset-root>:/data:ro scarf-slam:ros2-ovslam-jazzy bash -lc \
     'source /ros2_ws/setup_ovslam.bash &&
      ros2 bag info /data/r05/r05_bag'
   ```

   期望输入 topic：

   ```text
   /insta/cam0/image_raw/compressed  sensor_msgs/msg/CompressedImage
   /insta/imu/data_raw               sensor_msgs/msg/Imu
   /insta/poses_gt                   nav_msgs/msg/Path
   ```

2. 使用原生 ROS2 OV-SLAM launch 运行 R05。

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

   等待播放结束。确认 loop-fusion 节点输出以下日志：

   ```text
   auto-saved pose graph and closed bag writer after 5s idle with no pending optimization
   ```

   出现该信息后，如果节点没有自行退出，可以手动中断 launch。

3. 检查生成的 OV-SLAM 输出 bag。

   ```bash
   docker run --rm -v <dataset-root>:/data:ro scarf-slam:ros2-ovslam-jazzy bash -lc \
     'source /ros2_ws/setup_ovslam.bash &&
      ros2 bag info /data/r05/ov_slam_ros2_image/ov_slam/ov_slam_bag'
   ```

   期望输出 topic：

   ```text
   /ov_slam/image/compressed
   /ov_slam/odometry
   /ov_slam/trajectory
   /ov_slam/trajectory_final
   ```

4. 将 OV-SLAM 位姿导出为 TUM 风格文本。

   使用 Docker 镜像中的 `rosbags` 读取：

   ```text
   /ov_slam/odometry
   /ov_slam/trajectory
   /ov_slam/trajectory_final
   ```

   写出以下列格式的文本文件：

   ```text
   # timestamp tx ty tz qx qy qz qw
   ```

   推荐输出文件：

   ```text
   <dataset-root>/r05/ov_slam_ros2_image/poses/ov_slam_odometry.txt
   <dataset-root>/r05/ov_slam_ros2_image/poses/ov_slam_trajectory_last.txt
   <dataset-root>/r05/ov_slam_ros2_image/poses/ov_slam_trajectory_final.txt
   ```

   loop-fusion 节点也会直接写出最终轨迹：

   ```text
   <dataset-root>/r05/ov_slam_ros2_image/ov_slam/trajectory_final.txt
   ```

5. 使用 Sim3 ATE 与 R05 真值比较。

   使用 `<dataset-root>/r05/r05_gt/poses_gt.txt` 作为真值。以 `0.01s` 时间戳容差匹配位姿，用轨迹平移估计 Sim3 对齐，然后计算平移 ATE RMSE、mean、median、p95 和 max。

   如果需要与之前的 ROS1 路线对比，应先将 ROS1 IMU/body 位姿输出转换为相机位置：

   ```text
   p_C_in_G = p_I_in_G + R_GI * p_C_in_I
   ```

   使用 `<project-root>/config/open_vins/kalibr_imucam_chain.yaml` 中的 `T_cam_imu`。

## 验证

- 输入 `ros2 bag info` 应报告一个 MCAP ROS2 bag，包含相机、IMU 和 GT path topic。
- 完整运行后应生成：

  ```text
  <dataset-root>/r05/ov_slam_ros2_image/ov_slam/ov_slam_bag/
  <dataset-root>/r05/ov_slam_ros2_image/ov_slam/pose_graph/
  <dataset-root>/r05/ov_slam_ros2_image/ov_slam/trajectory_final.txt
  ```

- R05 的预期输出 bag topic 数量：

  ```text
  /ov_slam/image/compressed       1486
  /ov_slam/odometry               1486
  /ov_slam/trajectory             1486
  /ov_slam/trajectory_final       1
  ```

- R05 的预期导出文本数量：

  ```text
  ov_slam_odometry.txt            1486 poses
  ov_slam_trajectory_last.txt     1486 poses
  ov_slam_trajectory_final.txt    1486 poses
  ```

- 本次运行中，以 `0.01s` 时间戳容差与 R05 真值比较得到的 Sim3 ATE：

  | 输出 | 匹配位姿数 | ATE RMSE |
  |---|---:|---:|
  | ROS1 `ov_msckf`，IMU 转相机 | 2539 | 0.171 m |
  | ROS1 `ov_secondary`，IMU 转相机 | 2535 | 0.223 m |
  | ROS2 `/ov_slam/odometry` | 1486 | 0.0838 m |
  | ROS2 `/ov_slam/trajectory_last` | 1486 | 0.0255 m |
  | ROS2 `/ov_slam/trajectory_final` | 1486 | 0.0397 m |

## 最终状态

- 原生 ROS2 OV-SLAM 输出目录：

  ```text
  <dataset-root>/r05/ov_slam_ros2_image
  ```

- 主要最终位姿文件：

  ```text
  <dataset-root>/r05/ov_slam_ros2_image/ov_slam/trajectory_final.txt
  ```

- 导出的最终位姿文件：

  ```text
  <dataset-root>/r05/ov_slam_ros2_image/poses/ov_slam_trajectory_final.txt
  ```

- 本次测得最好的轨迹：

  ```text
  <dataset-root>/r05/ov_slam_ros2_image/poses/ov_slam_trajectory_last.txt
  ```

- 原生 ROS2 路线比 ROS1 转换 bag 路线更接近论文级别的 R05 OV-SLAM 结果。

## 失败尝试 / 备注

- ROS1 转换 bag 路线在 R05 上的 Sim3 ATE 明显差于原生 ROS2 路线。
- ROS1 位姿文本是 IMU/body pose stream；ROS2 `/ov_slam/*` 输出是相机关键帧 pose stream，比较时需要谨慎。
- loop-fusion 进程在 autosave 后可能需要手动中断。只有在日志确认 pose graph 已保存且 bag writer 已关闭后再中断。

## 占位符实际值

- `<project-root>`：本地 ScaRF-SLAM 仓库根目录；个人路径前缀已省略。
- `<dataset-root>`：包含已准备好的 R05 输入数据的本地目录；个人路径前缀已省略。
