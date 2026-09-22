#!/usr/bin/env python3
"""
==================================================================
스크립트: spawn_car.launch.py
설명: Gazebo Sim 물리 시뮬레이션 환경을 실행하고, 4륜 차량 URDF 모델을
      가상 월드에 스폰(Spawn)하며, ros_gz_bridge와 robot_state_publisher를
      연동하는 통합 런치 파일입니다.
구동 단계:
  1. worlds/car_track.sdf, config/bridge.yaml, urdf/vehicle.urdf.xacro 경로 계산
  2. 로봇 모델을 Xacro 엔진으로 파싱
  3. gz sim 명령 프로세스 기동 (물리 시뮬레이터 및 3D GUI 팝업)
  4. ros_gz_sim의 create 노드를 통해 월드에 로봇 엔티티 동적 생성
  5. ros_gz_bridge 노드를 통해 bridge.yaml에 정의된 토픽 중계
  6. robot_state_publisher 노드를 통해 시뮬레이션 시간(use_sim_time: True) 동기화
사용법:
  ros2 launch my_vehicle spawn_car.launch.py
==================================================================
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    # -------------------------------------------------------------
    # 1. 파일 경로 계산
    # launch/, urdf/, worlds/, config/ 가 모두 같은 패키지 폴더 안에 있으므로
    # 이 파일 위치 기준으로 찾는다. (소스에서 직접 실행 / colcon 빌드 후 실행 모두 동작)
    # -------------------------------------------------------------
    pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    world_file  = os.path.join(pkg_dir, 'worlds', 'car_track.sdf')
    bridge_yaml = os.path.join(pkg_dir, 'config', 'bridge.yaml')
    xacro_file  = os.path.join(pkg_dir, 'urdf', 'vehicle.urdf.xacro')

    # -------------------------------------------------------------
    # 2. Xacro 전처리 및 URDF XML 문자열 추출
    # -------------------------------------------------------------
    if not os.path.exists(xacro_file):
        raise FileNotFoundError(f'Xacro 파일을 찾을 수 없습니다: {xacro_file}')
    robot_description_content = xacro.process_file(xacro_file).toxml()

    # -------------------------------------------------------------
    # 3. Gazebo Sim 기동 (ros_gz_sim 의 gz_sim.launch.py 를 include)
    # - 'gz' 명령을 직접 부르지 않고 ros_gz_sim 이 제공하는 런치를 사용하면
    #   Gazebo 가 vendor 경로(/opt/ros/<distro>/opt/gz_*_vendor)에 설치된 경우에도
    #   PATH 설정과 무관하게 실행됨 (PPT 실습 6단계 방식)
    # - gz_args 의 -r: 일시정지가 아닌 즉시 실행(Run) 상태로 시작
    # -------------------------------------------------------------
    gz_sim_launch = os.path.join(
        get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
    gz_sim_process = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_sim_launch),
        launch_arguments={'gz_args': f'-r {world_file}'}.items()
    )

    # -------------------------------------------------------------
    # 4. ros_gz_sim 'create' 노드로 모델 스폰
    # 월드 좌표 (x=0, y=-4, z=0.15) 에 차량 생성.
    # Gazebo가 월드를 다 띄우기 전에 스폰 요청이 가면 실패할 수 있어 3초 뒤에 실행.
    # -------------------------------------------------------------
    spawn_car_node = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_car',
        output='screen',
        arguments=[
            '-name', 'auto_vehicle',
            '-string', robot_description_content,
            '-x', '0.0',
            '-y', '-4.0',
            '-z', '0.15'
        ]
    )
    spawn_car_delayed = TimerAction(period=3.0, actions=[spawn_car_node])

    # -------------------------------------------------------------
    # 5. ros_gz_bridge: bridge.yaml 설정대로 /clock, /cmd_vel, /odom 등 중계
    # -------------------------------------------------------------
    gz_bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='ros_gz_bridge',
        output='screen',
        parameters=[{
            'config_file': bridge_yaml
        }]
    )

    # -------------------------------------------------------------
    # 6. robot_state_publisher: use_sim_time=True 로 /clock 기준 TF 발행
    # -------------------------------------------------------------
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': True
        }]
    )

    return LaunchDescription([
        gz_sim_process,
        spawn_car_delayed,
        gz_bridge_node,
        robot_state_publisher_node
    ])
