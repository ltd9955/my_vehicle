#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
9주차 도전 미션 런치 파일: 과거 5초 궤적 그라데이션 마커 + RViz2
  - trail_marker_publisher : 가상 차량 TF(odom->base_link)와 /trajectory_trail 발행
  - rviz2                  : Fixed Frame 을 odom 으로 둔 trail_view.rviz 로드
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_dir = get_package_share_directory('my_viz_pkg')
    rviz_config_path = os.path.join(package_dir, 'config', 'trail_view.rviz')

    rviz_arg = DeclareLaunchArgument(
        'rviz', default_value='true', description='RViz2를 함께 실행할지 여부 (true/false)')

    trail_node = Node(
        package='my_viz_pkg',
        executable='trail_marker_publisher',
        name='trail_marker_publisher',
        output='screen',
        emulate_tty=True,
    )

    rviz_process = ExecuteProcess(
        cmd=['rviz2', '-d', rviz_config_path],
        output='screen',
        condition=IfCondition(LaunchConfiguration('rviz'))
    )

    return LaunchDescription([
        rviz_arg,
        LogInfo(msg='[9주차 도전] 과거 5초 궤적 그라데이션 마커를 가동합니다.'),
        trail_node,
        rviz_process,
    ])
