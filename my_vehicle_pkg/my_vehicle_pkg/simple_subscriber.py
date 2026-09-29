from rclpy.node import Node
from std_msgs.msg import String
import rclpy


class SimpleSubscriber(Node):
    def __init__(self):
        super().__init__('simple_subscriber')
        self.subscription = self.create_subscription(
            String, '/vehicle_status', self.listener_callback, 10)

    def listener_callback(self, msg):
        self.get_logger().info(f'Subscribed: "{msg.data}"')


def main(args=None):
    rclpy.init(args=args)
    ss = SimpleSubscriber()
    rclpy.spin(ss)
    ss.destroy_node()
    rclpy.shutdown()
