#!/usr/bin/env python3
"""
==================================================================
스크립트: display.launch.py
설명: 차량 로봇 모델(URDF/Xacro)을 RViz2에서 시각화하기 위한 런치 파일.
동작 흐름:
  1. urdf/vehicle.urdf.xacro 파일을 Xacro 전처리기로 파싱
  2. robot_state_publisher 노드에 모델 XML 문자열 주입 및 실행
  3. joint_state_publisher_gui 노드를 실행하여 슬라이더 GUI 제공
  4. RViz2 노드를 rviz/display.rviz 설정으로 실행
     (Fixed Frame=base_link, RobotModel 포함 → 별도 설정 없이 바로 차량이 보임)
사용법:
  ros2 launch my_vehicle display.launch.py
==================================================================
"""

import os
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    # 1. 파일 경로 계산
    # launch/ 와 urdf/, rviz/ 가 같은 패키지 폴더 안에 있으므로, 이 파일 위치 기준으로 찾는다.
    # (소스 폴더에서 직접 실행하든, colcon 빌드 후 share/my_vehicle/ 에서 실행하든 동일하게 동작)
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xacro_path = os.path.join(pkg_dir, 'urdf', 'vehicle.urdf.xacro')
    rviz_config = os.path.join(pkg_dir, 'rviz', 'display.rviz')

    # 2. Xacro 전처리 → 순수 URDF XML 문자열
    robot_description_raw = xacro.process_file(xacro_path).toxml()

    # 3. robot_state_publisher: /joint_states 를 구독하여 /tf, /tf_static 발행
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_raw,
            'use_sim_time': False
        }]
    )

    # 4. joint_state_publisher_gui: 슬라이더로 관절 각도를 조작해 /joint_states 발행
    node_joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen'
    )

    # 5. RViz2: 저장된 설정 파일(-d)로 실행
    node_rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        # WSL/Wayland 환경에서 Qt 창이 안 뜨는 문제 방지 (네이티브 Ubuntu에서도 무해)
        additional_env={'QT_QPA_PLATFORM': 'xcb'}
    )

    return LaunchDescription([
        node_robot_state_publisher,
        node_joint_state_publisher_gui,
        node_rviz2
    ])
