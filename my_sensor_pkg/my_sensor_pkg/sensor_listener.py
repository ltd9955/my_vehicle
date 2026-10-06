#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
오토모티브SW프로그래밍 6주차 실습 코드: Best Effort QoS 기반 다중 센서 수신 및 전처리 노드
작성자: 김동주 교수 (deekim@cu.ac.kr)

[설명]
자율주행 차량의 3대 핵심 센서인 LiDAR(/scan), IMU(/imu/data), 카메라(/camera/image_raw)의
데이터를 수신하고 실시간 전처리를 수행하는 노드입니다.

[핵심 개념]
- Best Effort QoS: 대용량 고주파 센서 스트림에서 패킷 재전송에 따른 지연(Latency)을 방지
- MultiThreadedExecutor: 단일 스레드 이벤트 루프의 병목을 없애고 다중 센서 콜백을 병렬 처리
- ReentrantCallbackGroup: 여러 센서 콜백이 스레드 풀에서 서로를 블로킹하지 않고 동시 진입 허용
- LaserScan 전처리: 전방 유효 거리 필터링 및 최근접 장애물 거리/각도 계산
- IMU 자세 유도: 단위 쿼터니언으로부터 차체의 기울기(Roll, Pitch) 복원
"""

import math
import sys
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from sensor_msgs.msg import LaserScan, Imu, Image


class SensorListenerNode(Node):
    """
    3대 자율주행 센서 데이터를 Best Effort QoS 및 멀티스레드로 수신하는 노드입니다.
    """

    def __init__(self):
        super().__init__('sensor_listener_node')

        # 1. 멀티스레드 병렬 실행을 위한 재진입 콜백 그룹 생성
        # 이 그룹에 속한 콜백 함수들은 별도의 작업 스레드에서 동시에 실행될 수 있습니다.
        self.callback_group = ReentrantCallbackGroup()

        # 2. 고주파 센서 스트림 전용 Best Effort QoS 프로파일 정의
        # - reliability = BEST_EFFORT: 손실 시 재전송을 생략하여 실시간성(최신성) 보장
        # - history = KEEP_LAST: 최신 N개 데이터만 수신 큐에 유지
        # - depth = 10: 큐 오버플로 및 메모리 팽창 방지
        # - durability = VOLATILE: 늦게 실행된 노드에게 과거 센서 데이터를 보내지 않음
        self.sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
            durability=DurabilityPolicy.VOLATILE
        )

        # 3. 2D 라이다 센서 토픽 구독 (/scan, 약 10Hz)
        self.scan_sub = self.create_subscription(
            LaserScan,
            '/scan',
            self.scan_callback,
            self.sensor_qos,
            callback_group=self.callback_group
        )

        # 4. IMU 관성 센서 토픽 구독 (/imu/data, 약 50Hz)
        self.imu_sub = self.create_subscription(
            Imu,
            '/imu/data',
            self.imu_callback,
            self.sensor_qos,
            callback_group=self.callback_group
        )

        # 5. 전방 RGB 카메라 토픽 구독 (/camera/image_raw, 약 30Hz)
        self.camera_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.camera_callback,
            self.sensor_qos,
            callback_group=self.callback_group
        )

        # 카메라 수신 통계용 변수
        self.camera_frame_count = 0

        self.get_logger().info(
            '센서 통합 리스너 노드 초기화 완료 (Best Effort QoS & MultiThreadedExecutor 적용)'
        )

    def scan_callback(self, msg: LaserScan):
        """
        라이다 스캔 콜백: ranges 배열에서 유효 거리를 탐색하고
        가장 가까운 장애물까지의 거리와 각도를 계산합니다.
        """
        # (1) 유효 측정 범위(range_min ~ range_max) 내의 값만 필터링
        valid_ranges = [
            r for r in msg.ranges
            if not math.isnan(r) and not math.isinf(r) and (msg.range_min < r < msg.range_max)
        ]

        if not valid_ranges:
            self.get_logger().info('[라이다] 유효한 반사 장애물이 감지되지 않았습니다.')
            return

        # (2) 가장 가까운 장애물 거리 계산
        min_distance = min(valid_ranges)
        min_index = msg.ranges.index(min_distance)

        # (3) 최소 거리 지점의 방위 각도(Angle) 계산
        # angle = angle_min + (index * angle_increment)
        detect_angle_rad = msg.angle_min + (min_index * msg.angle_increment)
        detect_angle_deg = math.degrees(detect_angle_rad)

        # (4) 1미터 이내 전방 장애물 근접 시 긴급 경고 출력
        if min_distance < 1.0:
            self.get_logger().warning(
                f'[라이다 긴급경고] 전방 장애물 초근접! '
                f'거리: {min_distance:4.2f}m | 각도: {detect_angle_deg:+5.1f}°'
            )
        else:
            self.get_logger().info(
                f'[라이다] 최근접 물체 거리: {min_distance:4.2f}m | 각도: {detect_angle_deg:+5.1f}°'
            )

    def imu_callback(self, msg: Imu):
        """
        IMU 콜백: 쿼터니언 자세로부터 차체의 Roll(좌우 기울기), Pitch(앞뒤 기울기)를 복원합니다.
        """
        q = msg.orientation

        # 쿼터니언 (x, y, z, w) -> 오일러 각 변환 공식
        # Roll = atan2(2*(w*x + y*z), 1 - 2*(x^2 + y^2))
        sinr_cosp = 2.0 * (q.w * q.x + q.y * q.z)
        cosr_cosp = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
        roll_deg = math.degrees(math.atan2(sinr_cosp, cosr_cosp))

        # Pitch = asin(2*(w*y - z*x))
        sinp = 2.0 * (q.w * q.y - q.z * q.x)
        if abs(sinp) >= 1.0:
            pitch_deg = math.copysign(90.0, sinp)  # 짐벌 락 영역 보호
        else:
            pitch_deg = math.degrees(math.asin(sinp))

        # 차체가 10도 이상 급격히 기울어지면 주의 경고 출력
        if abs(roll_deg) > 10.0 or abs(pitch_deg) > 10.0:
            self.get_logger().warning(
                f'[IMU 경고] 차체 급경사/기울기 감지! Roll={roll_deg:+5.1f}°, Pitch={pitch_deg:+5.1f}°'
            )

    def camera_callback(self, msg: Image):
        """
        카메라 콜백: 고용량 이미지 스트림의 해상도, 인코딩 포맷 및 프레임 빈도를 주기적으로 모니터링합니다.
        """
        self.camera_frame_count += 1

        # 30프레임마다 한 번씩(약 1초 간격) 상태 요약 로깅
        if self.camera_frame_count % 30 == 0:
            data_size_kb = len(msg.data) / 1024.0
            self.get_logger().info(
                f'[카메라 수신] 프레임 #{self.camera_frame_count:04d} | '
                f'해상도: {msg.width}x{msg.height} | 포맷: {msg.encoding} | '
                f'프레임 크기: {data_size_kb:6.1f} KB'
            )


def main(args=None):
    """멀티스레드 실행기(MultiThreadedExecutor)를 통한 노드 기동"""
    rclpy.init(args=args)
    node = SensorListenerNode()

    # 4개의 워커 스레드를 가진 멀티스레드 실행기 생성
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info('사용자 인터럽트로 센서 리스너 노드를 종료합니다.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
