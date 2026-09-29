from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(package='my_vehicle_pkg', executable='simple_publisher', name='pub_node'),
        Node(package='my_vehicle_pkg', executable='simple_subscriber', name='sub_node'),
    ])
