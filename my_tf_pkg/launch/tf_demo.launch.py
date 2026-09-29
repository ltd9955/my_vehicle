import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    rviz_config = os.path.join(
        get_package_share_directory('my_tf_pkg'), 'rviz', 'tf_demo.rviz')

    return LaunchDescription([
        Node(
            package='my_tf_pkg',
            executable='static_tf_broadcaster',
            name='static_tf_broadcaster',
            output='screen',
        ),
        Node(
            package='my_tf_pkg',
            executable='dynamic_tf_broadcaster',
            name='dynamic_tf_broadcaster',
            output='screen',
        ),
        Node(
            package='my_tf_pkg',
            executable='tf_listener',
            name='tf_listener',
            output='screen',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config],
            output='screen',
        ),
    ])
