#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
오토모티브SW프로그래밍 5주차 실습 코드: 정적 TF 브로드캐스터
작성자: 김동주 교수 (deekim@cu.ac.kr)

[설명]
차량 중심(base_link)에서 전방 범퍼 상단에 장착된 2D 라이다(lidar_link)로의
물리적 상대 위치(오프셋)를 1회 정적으로 발행하는 ROS 2 노드입니다.

[핵심 개념]
- /tf_static 토픽 활용: 고정된 센서 장착 위치는 매 주기마다 다시 보낼 필요가 없음
- Transient Local Durability QoS: 뒤늦게 실행된 노드도 DDS 캐시로부터 과거 메시지를 즉시 전달받음
- TransformStamped: 부모 프레임, 자식 프레임, 3차원 평행이동, 쿼터니언 회전을 담는 표준 메시지
"""

import sys
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
import tf2_ros


class StaticTfBroadcaster(Node):
    """
    차량 기준 좌표계(base_link)와 라이다 센서 좌표계(lidar_link) 간의
    불변 기하학적 관계를 브로드캐스팅하는 노드입니다.
    """

    def __init__(self):
        super().__init__('static_tf_broadcaster')

        # 1. 정적 변환 브로드캐스터 객체 생성
        # 내부적으로 /tf_static 토픽에 대해 Transient Local QoS 퍼블리셔를 자동으로 구성합니다.
        self.tf_static_broadcaster = tf2_ros.StaticTransformBroadcaster(self)

        # 2. 정적 변환 메시지 생성 및 1회 발행
        self.broadcast_static_transform()

    def broadcast_static_transform(self):
        """
        base_link -> lidar_link 변환 메시지를 생성하고 /tf_static으로 전송합니다.
        """
        transform_stamped = TransformStamped()

        # (1) 시간 스탬프 설정 (현재 ROS 시간)
        transform_stamped.header.stamp = self.get_clock().now().to_msg()

        # (2) 부모 좌표계(Parent Frame)와 자식 좌표계(Child Frame) 지정
        # 차량 중심(base_link)을 기준으로 라이다(lidar_link)의 위치를 기술합니다.
        transform_stamped.header.frame_id = 'base_link'
        transform_stamped.child_frame_id = 'lidar_link'

        # (3) 3차원 평행이동 오프셋 (단위: 미터)
        # 차량 중심에서 전방(X)으로 +0.5m, 좌우(Y)로 0.0m, 상방(Z)으로 +0.3m 위치
        transform_stamped.transform.translation.x = 0.5
        transform_stamped.transform.translation.y = 0.0
        transform_stamped.transform.translation.z = 0.3

        # (4) 3차원 회전 (단위 쿼터니언: Quaternion)
        # 센서의 축 방향이 차체와 완벽히 평행하게 정렬되어 있으므로 회전 각도는 0도입니다.
        # 단위 쿼터니언의 정의: x=0, y=0, z=0, w=1
        transform_stamped.transform.rotation.x = 0.0
        transform_stamped.transform.rotation.y = 0.0
        transform_stamped.transform.rotation.z = 0.0
        transform_stamped.transform.rotation.w = 1.0

        # (5) 브로드캐스터를 통해 메시지 전송
        self.tf_static_broadcaster.sendTransform(transform_stamped)

        self.get_logger().info(
            '정적 TF 변환 발행 완료: [base_link -> lidar_link] '
            '(Translation: x=0.5m, y=0.0m, z=0.3m | Rotation: Quaternion(0,0,0,1))'
        )


def main(args=None):
    """노드 초기화 및 메인 이벤트 루프 실행"""
    rclpy.init(args=args)
    node = StaticTfBroadcaster()

    try:
        # 노드를 상주시켜 Late-Joiner 노드에게 지속적으로 /tf_static을 서비스합니다.
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('사용자 인터럽트로 노드를 종료합니다.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
