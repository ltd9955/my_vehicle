#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
오토모티브SW프로그래밍 5주차 실습 코드: TF2 버퍼 및 룩업 리스너 노드
작성자: 김동주 교수 (deekim@cu.ac.kr)

[설명]
TF2 라이브러리의 핵심 자료구조인 시간 기반 링 버퍼(Buffer)와 리스너(TransformListener)를
초기화하여, 백그라운드에서 /tf 및 /tf_static 토픽을 자동 구독하여 내부 트리를 유지합니다.
주기적인 타이머(10Hz)를 통해 전역 오도메트리 원점(odom)을 기준으로
차량 범퍼에 장착된 2D 라이다 센서(lidar_link)의 실시간 3차원 위치를
lookup_transform API로 질의(Lookup)하여 계산합니다.

[핵심 개념]
- tf2_ros.Buffer: 과거 10초간의 시계열 변환을 저장하고 관리하는 링 버퍼
- tf2_ros.TransformListener: 노드와 버퍼를 연결하여 TF 토픽 수신을 전담하는 객체
- lookup_transform: 기준 좌표계와 대상 좌표계 간의 변환 행렬을 트리 탐색 및 보간(SLERP)을 거쳐 산출
- TransformException: 변환 트리가 아직 완성되지 않았거나 지연이 발생할 때 안전하게 처리하는 예외 클래스
"""

import math
import sys
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
import tf2_ros
from tf2_ros import TransformException


class TfListenerNode(Node):
    """
    TF2 변환 트리를 구독하고, odom 좌표계 기준 lidar_link 센서의
    실시간 3차원 위치를 주기적으로 조회하여 출력하는 리스너 노드입니다.
    """

    def __init__(self):
        super().__init__('tf_listener_node')

        # 1. TF 버퍼 객체 생성
        # 내부적으로 링 버퍼(Ring Buffer) 구조를 가지며 기본 10초간의 변환 히스토리를 보관합니다.
        self.tf_buffer = tf2_ros.Buffer()

        # 2. TF 리스너 객체 생성
        # 생성되는 즉시 백그라운드에서 /tf 토픽과 /tf_static 토픽을 구독하여
        # 수신되는 모든 변환 데이터를 self.tf_buffer에 자동으로 차곡차곡 채웁니다.
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # 3. 10Hz 주기 타이머 생성 (100ms 간격으로 룩업 질의 수행)
        timer_period = 0.1
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info(
            'TF2 리스너 노드 가동 완료: 10Hz 주기로 [odom -> lidar_link] 합성 변환 질의 시작'
        )

    def timer_callback(self):
        """
        타이머 콜백: 버퍼에 질의하여 odom 기준 lidar_link의 합성 위치를 산출합니다.
        """
        # 목표 기준 프레임 (Target Frame): 관찰자의 기준 좌표계
        target_frame = 'odom'
        # 질의 대상 프레임 (Source Frame): 위치를 알고자 하는 센서 좌표계
        source_frame = 'lidar_link'

        try:
            # lookup_transform 호출:
            # - target_frame: 'odom'
            # - source_frame: 'lidar_link'
            # - time: rclpy.time.Time() -> 타임스탬프를 0으로 넘기면 '버퍼 내 가장 최신 변환'을 요청함
            # - timeout: 네트워크 전송 지연을 감안하여 변환이 도착할 때까지 최대 50ms 동안 블로킹 대기
            transform = self.tf_buffer.lookup_transform(
                target_frame=target_frame,
                source_frame=source_frame,
                time=rclpy.time.Time(),
                timeout=Duration(seconds=0.05)
            )

            # 3차원 평행이동 좌표 추출
            trans_x = transform.transform.translation.x
            trans_y = transform.transform.translation.y
            trans_z = transform.transform.translation.z

            # 4원수 쿼터니언 회전 성분 추출
            rot_x = transform.transform.rotation.x
            rot_y = transform.transform.rotation.y
            rot_z = transform.transform.rotation.z
            rot_w = transform.transform.rotation.w

            # 원점(0, 0)으로부터의 2D 유클리드 거리 계산
            dist_from_origin = math.hypot(trans_x, trans_y)

            # 쿼터니언으로부터 수평 방향각(Yaw) 복원:
            # yaw = atan2(2*(w*z + x*y), 1 - 2*(y^2 + z^2))
            siny_cosp = 2.0 * (rot_w * rot_z + rot_x * rot_y)
            cosy_cosp = 1.0 - 2.0 * (rot_y * rot_y + rot_z * rot_z)
            yaw_rad = math.atan2(siny_cosp, cosy_cosp)
            yaw_deg = math.degrees(yaw_rad)

            # 콘솔에 정돈된 형식으로 결과 출력
            self.get_logger().info(
                f'[TF 룩업 성공] {target_frame} -> {source_frame} | '
                f'위치(X={trans_x:5.2f}m, Y={trans_y:5.2f}m, Z={trans_z:4.2f}m) | '
                f'원점거리={dist_from_origin:4.2f}m | Yaw={yaw_deg:6.1f}°'
            )

        except TransformException as ex:
            # 브로드캐스터가 아직 켜지지 않았거나, 버퍼 보간 범위를 벗어난 경우 발생하는 예외
            # 노드가 다운되지 않도록 warn 로그를 남기며 안전하게 통과합니다.
            self.get_logger().warning(f'TF 변환 조회 대기 중... ({ex})')


def main(args=None):
    """노드 초기화 및 실행"""
    rclpy.init(args=args)
    node = TfListenerNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('사용자 인터럽트로 TF 리스너를 종료합니다.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
