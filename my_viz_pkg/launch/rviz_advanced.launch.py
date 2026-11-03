#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
강의명: 오토모티브SW프로그래밍
주차: 9주차
파일명: rviz_advanced.launch.py
설명: 커스텀 마커 발행 노드(custom_marker_publisher)와
      사전 구성된 RViz2 시각화 화면을 동시에 실행하는 ROS 2 Python 런치 파일

원본(code09)과 달라진 점:
  - 패키지/실행 파일 이름을 my_viz_pkg / custom_marker_publisher 로 맞춤
  - RViz2 Fixed Frame 이 base_link 인데 이를 발행하는 TF 소스가 없어 마커가 그려지지 않으므로
    odom -> base_link 정적 TF 발행 노드를 추가
  - rviz 런치 인자(true/false) 추가: 노드만 검증할 때 RViz2 없이 실행 가능
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """
    ROS 2 런치 디스크립션 생성 함수
    """

    # 1. 파일 경로: 설치된 패키지 share 폴더의 config/integrated_view.rviz
    package_dir = get_package_share_directory('my_viz_pkg')
    rviz_config_path = os.path.join(package_dir, 'config', 'integrated_view.rviz')

    # 2. 런치 인자 선언
    frame_id_arg = DeclareLaunchArgument(
        'frame_id',
        default_value='base_link',
        description='마커 기준 좌표계 (기본값: base_link)'
    )
    publish_rate_arg = DeclareLaunchArgument(
        'publish_rate',
        default_value='10.0',
        description='마커 발행 주기(Hz)'
    )
    obstacle_dist_arg = DeclareLaunchArgument(
        'obstacle_distance',
        default_value='4.0',
        description='전방 가상 장애물 초기 거리(m)'
    )
    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        description='RViz2를 함께 실행할지 여부 (true/false)'
    )

    # 3. TF 소스: Fixed Frame(base_link)이 존재해야 RViz2가 마커를 그린다.
    base_link_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='odom_to_base_link_tf',
        arguments=['--x', '0', '--y', '0', '--z', '0',
                   '--roll', '0', '--pitch', '0', '--yaw', '0',
                   '--frame-id', 'odom', '--child-frame-id', 'base_link'],
        output='screen'
    )

    # 4. 커스텀 마커 퍼블리셔 노드
    marker_node = Node(
        package='my_viz_pkg',
        executable='custom_marker_publisher',
        name='custom_marker_publisher',
        output='screen',
        emulate_tty=True,
        parameters=[{
            'frame_id': LaunchConfiguration('frame_id'),
            'publish_rate': LaunchConfiguration('publish_rate'),
            'obstacle_distance': LaunchConfiguration('obstacle_distance')
        }]
    )

    # 5. RViz2 (사전 설정 파일 로드)
    rviz_process = ExecuteProcess(
        cmd=['rviz2', '-d', rviz_config_path],
        output='screen',
        condition=IfCondition(LaunchConfiguration('rviz'))
    )

    start_log = LogInfo(
        msg='[오토모티브SW프로그래밍 9주차] RViz2 심화 시각화 시스템을 가동합니다.'
    )

    return LaunchDescription([
        frame_id_arg,
        publish_rate_arg,
        obstacle_dist_arg,
        rviz_arg,
        start_log,
        base_link_tf,
        marker_node,
        rviz_process
    ])
