import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'my_viz_pkg'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ltd9955',
    maintainer_email='ltd9955@todo.todo',
    description='Week 9 - RViz2 custom markers',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'custom_marker_publisher = my_viz_pkg.custom_marker_publisher:main',
            'trail_marker_publisher = my_viz_pkg.trail_marker_publisher:main',
        ],
    },
)
