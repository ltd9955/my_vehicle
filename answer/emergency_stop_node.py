#!/usr/bin/env python3
"""6주차 과제 1: 라이다 기반 전방 긴급 정지(EMERGENCY_STOP) 경고 노드.

/scan 을 Best Effort QoS 로 구독하여 정면 +-20도 부채꼴 안에서
1.0m 이내 장애물이 감지되면 붉은색(ERROR) 로그로 경고한다.
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

FRONT_HALF_ANGLE = math.radians(20.0)
STOP_DISTANCE = 1.0


def find_front_obstacle(msg: LaserScan):
    """정면 부채꼴 안에서 가장 가까운 유효 거리와 그 각도(rad)를 반환한다.

    유효한 측정값이 없으면 None 을 반환한다.
    """
    nearest = None
    for i, r in enumerate(msg.ranges):
        # 각도는 [-pi, pi] 로 정규화한다 (angle_min 이 0 인 라이다 대응).
        raw = msg.angle_min + i * msg.angle_increment
        angle = math.atan2(math.sin(raw), math.cos(raw))

        # 정확히 +-20도 샘플이 부동소수점 오차로 빠지지 않도록 작은 허용 오차를 둔다.
        if abs(angle) > FRONT_HALF_ANGLE + 1e-6:
            continue
        # inf / nan / 측정 범위 밖(0.0 노이즈 포함) 값은 버린다.
        if not math.isfinite(r) or not (msg.range_min < r < msg.range_max):
            continue

        if nearest is None or r < nearest[0]:
            nearest = (r, angle)
    return nearest


class EmergencyStopNode(Node):
    def __init__(self):
        super().__init__('emergency_stop_node')
        # qos_profile_sensor_data = BEST_EFFORT + VOLATILE + KEEP_LAST(5)
        self.create_subscription(
            LaserScan, '/scan', self.scan_callback, qos_profile_sensor_data)
        self.get_logger().info(
            f'긴급 정지 감시 시작: 정면 ±{math.degrees(FRONT_HALF_ANGLE):.0f}°, '
            f'{STOP_DISTANCE:.1f}m 이내 (Best Effort QoS)')

    def scan_callback(self, msg: LaserScan):
        nearest = find_front_obstacle(msg)
        if nearest is None:
            return

        distance, angle = nearest
        if distance <= STOP_DISTANCE:
            # ERROR 레벨은 터미널에서 붉은색으로 출력된다.
            self.get_logger().error(
                f'[EMERGENCY_STOP] 전방 장애물 감지! '
                f'거리: {distance:.2f}m | 각도: {math.degrees(angle):+.1f}°',
                throttle_duration_sec=0.5)


def main(args=None):
    rclpy.init(args=args)
    node = EmergencyStopNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
