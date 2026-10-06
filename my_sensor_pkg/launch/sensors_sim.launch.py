import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    vehicle_launch = os.path.join(
        get_package_share_directory('my_vehicle'), 'launch', 'spawn_car.launch.py')
    bridge_yaml = os.path.join(
        get_package_share_directory('my_sensor_pkg'), 'config', 'sensor_bridge.yaml')

    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(vehicle_launch)),
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='sensor_parameter_bridge',
            parameters=[{'config_file': bridge_yaml}],
            output='screen',
        ),
        Node(
            package='my_sensor_pkg',
            executable='sensor_listener',
            name='sensor_listener_node',
            output='screen',
        ),
    ])
