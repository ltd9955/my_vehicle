#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
강의명: 오토모티브SW프로그래밍
주차: 9주차
파일명: custom_marker_publisher.py
설명: 가상 주행 경로(LINE_STRIP), 3D 장애물(CUBE), 위험도 안내 텍스트(TEXT_VIEW_FACING)를
      생성하여 MarkerArray 토픽으로 실시간 발행하는 RViz2 심화 시각화 노드.
"""

import math
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA
from builtin_interfaces.msg import Duration


class CustomMarkerPublisherNode(Node):
    """
    자율주행 차량의 경로 계획 및 센서 인식 결과를
    RViz2 3D 마커(MarkerArray)로 실시간 변환 및 퍼블리시하는 노드
    """

    def __init__(self):
        super().__init__('custom_marker_publisher')

        # =====================================================================
        # 1. 파라미터 선언 (외부 Launch 및 YAML에서 동적 변경 가능)
        # =====================================================================
        self.declare_parameter('frame_id', 'base_link')    # 기준 좌표계 (차량 기준 프레임)
        self.declare_parameter('publish_rate', 10.0)       # 토픽 발행 주기 (Hz)
        self.declare_parameter('obstacle_distance', 4.0)   # 전방 장애물 초기 거리 (m)

        self.frame_id = self.get_parameter('frame_id').value
        self.publish_rate = self.get_parameter('publish_rate').value
        self.obstacle_distance = self.get_parameter('obstacle_distance').value

        # =====================================================================
        # 2. 토픽 퍼블리셔 생성
        #    - 복수의 마커를 묶어서 한 번에 보내는 MarkerArray 사용 (네트워크 효율 최적화)
        # =====================================================================
        self.marker_array_pub = self.create_publisher(
            MarkerArray,
            '/visual_markers',
            10
        )

        # =====================================================================
        # 3. 주기적 발행 타이머 가동 (10Hz)
        # =====================================================================
        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self.timer_callback)

        # 가상 주행 경로 및 장애물 동적 움직임을 시뮬레이션하기 위한 시간 변수
        self.time_step = 0.0

        self.get_logger().info(
            f'=== 커스텀 마커 퍼블리셔 노드 시작 ===\n'
            f'  - 기준 좌표계(frame_id): {self.frame_id}\n'
            f'  - 발행 주기: {self.publish_rate:.1f} Hz\n'
            f'  - 장애물 기준 거리: {self.obstacle_distance:.2f} m'
        )

    def timer_callback(self):
        """
        10Hz(0.1초) 주기로 실행되며, 3종류의 마커를 생성하여 MarkerArray로 일괄 발행
        """
        now = self.get_clock().now()
        marker_array = MarkerArray()

        # -------------------------------------------------------------
        # [메모리 누수 및 고스트 오브젝트 방지 핵심]
        # lifetime = 0.2초 설정
        # 10Hz(0.1초 간격)로 새 위치가 덮어써지는 동안은 매끄럽게 유지되지만,
        # 노드가 종료되거나 감지 대상이 사라지면 0.2초 후 RViz2 화면에서 자동 소멸됨
        # -------------------------------------------------------------
        marker_lifetime = Duration(sec=0, nanosec=200000000)  # 0.2초 (200,000,000 ns)

        # 애니메이션 시간 누적
        self.time_step += 0.05

        # =====================================================================
        # [마커 1] 가상 주행 계획선 (LINE_STRIP)
        # =====================================================================
        path_marker = Marker()
        path_marker.header.frame_id = self.frame_id
        path_marker.header.stamp = now.to_msg()
        path_marker.ns = 'trajectory'
        path_marker.id = 1
        path_marker.type = Marker.LINE_STRIP
        path_marker.action = Marker.ADD

        # 선의 굵기 (scale.x만 선 두께로 사용됨)
        path_marker.scale.x = 0.08

        # 에메랄드 그린 색상 및 85% 알파 블렌딩 적용
        path_marker.color = ColorRGBA(r=0.1, g=0.9, b=0.4, a=0.85)
        path_marker.lifetime = marker_lifetime

        # 전방 10m 곡선 궤적 점군(Point List) 생성
        for i in range(40):
            x = i * 0.25  # 전방 0m부터 10m까지 0.25m 간격
            y = 0.7 * math.sin(0.4 * x + self.time_step)  # 부드러운 S자 주행선
            z = 0.02      # 노면 위에 살짝 띄움 (Z-파이팅 방지)
            path_marker.points.append(Point(x=float(x), y=float(y), z=float(z)))

        marker_array.markers.append(path_marker)

        # =====================================================================
        # [마커 2] 감지된 전방 장애물 3D 바운딩 박스 (CUBE)
        # =====================================================================
        obs_marker = Marker()
        obs_marker.header.frame_id = self.frame_id
        obs_marker.header.stamp = now.to_msg()
        obs_marker.ns = 'obstacles'
        obs_marker.id = 101
        obs_marker.type = Marker.CUBE
        obs_marker.action = Marker.ADD

        # 장애물 3차원 위치 설정 (전방에서 좌우로 천천히 횡단하는 가상 보행자/차량)
        obs_x = float(self.obstacle_distance)
        obs_y = 0.8 * math.sin(self.time_step * 0.8)
        obs_z = 0.5  # 바닥에서 0.5m 높이 (박스 중심 좌표)

        obs_marker.pose.position.x = obs_x
        obs_marker.pose.position.y = obs_y
        obs_marker.pose.position.z = obs_z
        obs_marker.pose.orientation.w = 1.0  # 회전 없음 (기본 자세)

        # 박스 크기 (가로 0.8m, 세로 0.8m, 높이 1.0m)
        obs_marker.scale.x = 0.8
        obs_marker.scale.y = 0.8
        obs_marker.scale.z = 1.0

        # 반투명 오렌지-레드 경고 색상 (내부 관찰 가능하도록 알파 60% 적용)
        obs_marker.color = ColorRGBA(r=1.0, g=0.35, b=0.1, a=0.6)
        obs_marker.lifetime = marker_lifetime

        marker_array.markers.append(obs_marker)

        # =====================================================================
        # [마커 3] 카메라 시점 직면 경고 텍스트 라벨 (TEXT_VIEW_FACING)
        # =====================================================================
        text_marker = Marker()
        text_marker.header.frame_id = self.frame_id
        text_marker.header.stamp = now.to_msg()
        text_marker.ns = 'warning_labels'
        text_marker.id = 201
        text_marker.type = Marker.TEXT_VIEW_FACING
        text_marker.action = Marker.ADD

        # 텍스트 위치 (장애물 박스 정중앙 바로 윗부분)
        text_marker.pose.position.x = obs_x
        text_marker.pose.position.y = obs_y
        text_marker.pose.position.z = obs_z + 0.8  # 장애물 상단 0.8m 지점

        # 폰트 높이 (scale.z만 사용됨)
        text_marker.scale.z = 0.32

        # 텍스트 내용 계산 (유클리드 거리 산출)
        # RViz2 기본 글꼴(Liberation Sans)에는 한글 글리프가 없어 영문으로 표기한다.
        dist_to_obstacle = math.sqrt(obs_x**2 + obs_y**2)
        text_marker.text = f'WARNING: OBSTACLE DETECTED\nDistance: {dist_to_obstacle:.2f} m'

        # 순백색 불투명 텍스트 (가독성 극대화)
        text_marker.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
        text_marker.lifetime = marker_lifetime

        marker_array.markers.append(text_marker)

        # =====================================================================
        # 4. MarkerArray 토픽 일괄 전송
        # =====================================================================
        self.marker_array_pub.publish(marker_array)


def main(args=None):
    """
    ROS 2 노드 진입점 함수
    """
    rclpy.init(args=args)
    node = CustomMarkerPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('사용자 인터럽트로 마커 노드를 정상 종료합니다.')
    except ExternalShutdownException:
        # kill/pkill(SIGTERM) 같은 외부 종료 신호는 정상 종료로 처리한다 (트레이스백 방지)
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
