#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
9주차 도전 미션: 차량의 과거 5초 이동 궤적을 0.5초 간격 점 마커로 표시하고,
오래된 점일수록 점점 투명해지는 그라데이션으로 시각화하는 노드.

- 가상 차량이 odom 좌표계에서 원 궤도를 주행하며 odom -> base_link TF를 30Hz로 발행한다.
- 0.5초마다 차량 위치를 기록하고 최근 5초 분량만 유지한다 (오래된 점은 폐기).
- 점들은 Marker.POINTS 하나에 담고, 점마다 다른 알파(colors[])를 주어 그라데이션을 만든다.
- 모든 마커에 lifetime을 지정해, 노드가 종료되면 화면에서 자동 소멸한다.
"""

import math
from collections import deque

import rclpy
from builtin_interfaces.msg import Duration, Time
from geometry_msgs.msg import Point, TransformStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import ColorRGBA
from tf2_ros import TransformBroadcaster
from visualization_msgs.msg import Marker, MarkerArray


class TrailMarkerPublisherNode(Node):
    def __init__(self):
        super().__init__('trail_marker_publisher')

        self.declare_parameter('radius', 3.0)             # 가상 주행 원 궤도 반지름 (m)
        self.declare_parameter('angular_speed', 0.5)      # 궤도 각속도 (rad/s)
        self.declare_parameter('trail_duration', 5.0)     # 궤적 보관 시간 (초)
        self.declare_parameter('sample_interval', 0.5)    # 궤적 점 기록 간격 (초)
        self.declare_parameter('publish_rate', 10.0)      # 마커 발행 주기 (Hz)

        self.radius = self.get_parameter('radius').value
        self.angular_speed = self.get_parameter('angular_speed').value
        self.trail_duration = self.get_parameter('trail_duration').value
        self.sample_interval = self.get_parameter('sample_interval').value
        self.publish_rate = self.get_parameter('publish_rate').value

        self.tf_broadcaster = TransformBroadcaster(self)
        self.marker_pub = self.create_publisher(MarkerArray, '/trajectory_trail', 10)

        self.start_time = self.get_clock().now()
        self.history = deque()          # (경과 시간 t, x, y)
        self.last_sample_t = -1e9

        self.create_timer(1.0 / 30.0, self.tf_callback)
        self.create_timer(1.0 / self.publish_rate, self.marker_callback)

        self.get_logger().info(
            f'=== 궤적 그라데이션 노드 시작: 반지름 {self.radius} m, '
            f'과거 {self.trail_duration} s, {self.sample_interval} s 간격 ==='
        )

    def elapsed(self):
        return (self.get_clock().now() - self.start_time).nanoseconds / 1e9

    def pose_at(self, t):
        theta = self.angular_speed * t
        x = self.radius * math.cos(theta)
        y = self.radius * math.sin(theta)
        yaw = theta + math.pi / 2.0      # 원의 접선 방향이 차량 진행 방향
        return x, y, yaw

    def tf_callback(self):
        x, y, yaw = self.pose_at(self.elapsed())
        tf = TransformStamped()
        tf.header.stamp = self.get_clock().now().to_msg()
        tf.header.frame_id = 'odom'
        tf.child_frame_id = 'base_link'
        tf.transform.translation.x = x
        tf.transform.translation.y = y
        tf.transform.rotation.z = math.sin(yaw / 2.0)
        tf.transform.rotation.w = math.cos(yaw / 2.0)
        self.tf_broadcaster.sendTransform(tf)

    def marker_callback(self):
        t = self.elapsed()
        x, y, _ = self.pose_at(t)

        # 0.5초 간격으로 위치를 기록하고, 5초가 지난 점은 버린다.
        if t - self.last_sample_t >= self.sample_interval:
            self.history.append((t, x, y))
            self.last_sample_t = t
        while self.history and t - self.history[0][0] > self.trail_duration:
            self.history.popleft()

        lifetime = Duration(sec=0, nanosec=300000000)   # 0.3초 (발행 주기 0.1초의 3배)
        now = self.get_clock().now().to_msg()
        # base_link 프레임 마커는 stamp 를 0 으로 두어 RViz2가 '가장 최신 TF'로 변환하게 한다.
        # (현재 시각 stamp 는 TF 최신 시각보다 앞서 외삽 오류를 일으킨다)
        zero_stamp = Time()
        array = MarkerArray()

        # [마커 1] 과거 궤적 점들 (POINTS, 점마다 알파가 다른 그라데이션)
        trail = Marker()
        trail.header.frame_id = 'odom'
        trail.header.stamp = now
        trail.ns = 'trail'
        trail.id = 0
        trail.type = Marker.POINTS
        trail.action = Marker.ADD
        trail.scale.x = 0.3
        trail.scale.y = 0.3
        trail.color = ColorRGBA(r=1.0, g=0.6, b=0.0, a=1.0)
        trail.lifetime = lifetime
        trail.pose.orientation.w = 1.0

        samples = list(self.history) + [(t, x, y)]
        for ts, px, py in samples:
            age_ratio = min(max((t - ts) / self.trail_duration, 0.0), 1.0)
            alpha = 1.0 - 0.9 * age_ratio      # 새 점 1.0 -> 5초 전 점 0.1
            trail.points.append(Point(x=float(px), y=float(py), z=0.05))
            trail.colors.append(ColorRGBA(r=1.0, g=0.6, b=0.0, a=float(alpha)))
        array.markers.append(trail)

        # [마커 2] 현재 차량 위치 박스 (base_link 프레임에 고정)
        car = Marker()
        car.header.frame_id = 'base_link'
        car.header.stamp = zero_stamp
        car.ns = 'vehicle'
        car.id = 1
        car.type = Marker.CUBE
        car.action = Marker.ADD
        car.pose.position.z = 0.1
        car.pose.orientation.w = 1.0
        car.scale.x, car.scale.y, car.scale.z = 0.6, 0.3, 0.2
        car.color = ColorRGBA(r=0.1, g=0.4, b=0.9, a=0.9)
        car.lifetime = lifetime
        array.markers.append(car)

        # [마커 3] 설명 텍스트 (항상 화면을 향함)
        label = Marker()
        label.header.frame_id = 'base_link'
        label.header.stamp = zero_stamp
        label.ns = 'labels'
        label.id = 2
        label.type = Marker.TEXT_VIEW_FACING
        label.action = Marker.ADD
        label.pose.position.z = 0.8
        label.pose.orientation.w = 1.0
        label.scale.z = 0.3
        label.text = f'Past {self.trail_duration:.0f}s trail ({self.sample_interval}s interval)'
        label.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
        label.lifetime = lifetime
        array.markers.append(label)

        self.marker_pub.publish(array)


def main(args=None):
    rclpy.init(args=args)
    node = TrailMarkerPublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('사용자 인터럽트로 궤적 노드를 종료합니다.')
    except ExternalShutdownException:
        # kill/pkill(SIGTERM) 같은 외부 종료 신호는 정상 종료로 처리한다 (트레이스백 방지)
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
