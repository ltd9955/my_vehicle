#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
오토모티브SW프로그래밍 5주차 실습 코드: 동적 오도메트리 TF 브로드캐스터
작성자: 김동주 교수 (deekim@cu.ac.kr)

[설명]
차량이 고정된 오도메트리 원점(odom)을 기준으로 2차원 평면 상에서
반경 2.0m의 원형 궤적을 그리며 회전 주행하는 상황을 시뮬레이션합니다.
차량의 이동 위치와 헤딩 각도(Yaw)를 30Hz 주기로 계산하여
/tf 토픽에 동적 변환(odom -> base_link)을 연속 브로드캐스팅합니다.

[핵심 개념]
- /tf 토픽 활용: 시간에 따라 연속적으로 변하는 위치/자세를 고주파(30Hz) 스트림으로 전송
- 오일러 각(Yaw) -> 쿼터니언(Quaternion) 변환 공식
- rclpy Timer를 이용한 주기적 콜백 호출 메커니즘
"""

import math
import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
import tf2_ros


class DynamicTfBroadcaster(Node):
    """
    차량의 가상 주행 궤적에 따른 odom -> base_link 변환을
    30Hz 주기로 /tf 토픽에 연속 발행하는 동적 TF 브로드캐스터 노드입니다.
    """

    def __init__(self):
        super().__init__('dynamic_tf_broadcaster')

        # 1. 동적 TF 브로드캐스터 객체 생성 (/tf 토픽 전용)
        self.tf_broadcaster = tf2_ros.TransformBroadcaster(self)

        # 2. 가상 주행 궤적 파라미터 정의
        self.radius = 2.0         # 원형 궤적 반경 (단위: 미터)
        self.angular_vel = 0.5    # 각속도 (단위: rad/s, 약 28.6 deg/s)
        self.start_time = self.get_clock().now()

        # 3. 30Hz 주기 타이머 생성 (주기: 약 0.0333초 = 33.3ms)
        # 자율주행 제어 루프와 유사한 빈도로 TF를 지속 갱신합니다.
        timer_period = 1.0 / 30.0
        self.timer = self.create_timer(timer_period, self.timer_callback)

        self.get_logger().info(
            f'동적 오도메트리 TF 브로드캐스터 가동 시작: '
            f'30Hz 주기로 [odom -> base_link] 발행 (반경={self.radius}m, 각속도={self.angular_vel}rad/s)'
        )

    def timer_callback(self):
        """
        타이머 콜백: 경과 시간에 따른 원형 궤적 위치 및 방향각을 계산하고
        TF 메시지로 패킹하여 브로드캐스팅합니다.
        """
        now = self.get_clock().now()
        # 노드 시작 시점부터 경과된 시간 (초 단위)
        elapsed_sec = (now - self.start_time).nanoseconds / 1e9

        # (1) 2차원 원형 궤적 상의 위치 계산 (x, y)
        # x(t) = R * cos(omega * t)
        # y(t) = R * sin(omega * t)
        pos_x = self.radius * math.cos(self.angular_vel * elapsed_sec)
        pos_y = self.radius * math.sin(self.angular_vel * elapsed_sec)
        pos_z = 0.0  # 평면 주행이므로 Z축 고도 변화는 없음

        # (2) 차량 진행 방향 헤딩 각도(Yaw) 계산
        # 원형 궤적에서 접선(진행) 방향은 반지름 벡터 방향에서 +90도(pi/2 rad) 회전한 방향입니다.
        yaw = (self.angular_vel * elapsed_sec) + (math.pi / 2.0)

        # (3) 2D 평면 회전 각도(Yaw)를 4원수 쿼터니언(x, y, z, w)으로 변환
        # 평면 주행 시 Roll=0, Pitch=0 이므로 공식은 다음과 같이 매우 단순화됩니다:
        # qx = 0, qy = 0, qz = sin(yaw / 2), qw = cos(yaw / 2)
        qz = math.sin(yaw / 2.0)
        qw = math.cos(yaw / 2.0)

        # (4) TransformStamped 메시지 생성
        transform_stamped = TransformStamped()

        # 헤더 설정: 변환이 유효한 정확한 시간 스탬프 기록
        transform_stamped.header.stamp = now.to_msg()

        # 부모-자식 프레임 ID 설정
        # REP 105 표준에 따라 odom이 부모, base_link가 자식입니다.
        transform_stamped.header.frame_id = 'odom'
        transform_stamped.child_frame_id = 'base_link'

        # 평행이동 벡터 입력
        transform_stamped.transform.translation.x = pos_x
        transform_stamped.transform.translation.y = pos_y
        transform_stamped.transform.translation.z = pos_z

        # 회전 쿼터니언 입력
        transform_stamped.transform.rotation.x = 0.0
        transform_stamped.transform.rotation.y = 0.0
        transform_stamped.transform.rotation.z = qz
        transform_stamped.transform.rotation.w = qw

        # (5) /tf 토픽으로 동적 변환 브로드캐스팅
        self.tf_broadcaster.sendTransform(transform_stamped)


def main(args=None):
    """노드 초기화 및 실행"""
    rclpy.init(args=args)
    node = DynamicTfBroadcaster()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('사용자 인터럽트로 동적 브로드캐스터를 종료합니다.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
