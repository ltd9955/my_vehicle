from rclpy.node import Node
from std_msgs.msg import String
import rclpy


class SimplePublisher(Node):
    def __init__(self):
        super().__init__('simple_publisher')
        self.i = 0
        self.publisher_ = self.create_publisher(String, '/vehicle_status', 10)
        self.timer = self.create_timer(1.0, self.timer_callback)

    def timer_callback(self):
        msg = String()
        msg.data = f'Vehicle Speed: {self.i} km/h'
        self.publisher_.publish(msg)
        self.get_logger().info(f'Publishing: "{msg.data}"')
        self.i += 5


def main(args=None):
    rclpy.init(args=args)
    sp = SimplePublisher()
    rclpy.spin(sp)
    sp.destroy_node()
    rclpy.shutdown()
