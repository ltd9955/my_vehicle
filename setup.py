import os
from glob import glob
from setuptools import setup

package_name = 'my_vehicle'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        # ament 인덱스 등록: 이 항목이 있어야 `ros2 launch my_vehicle ...` 로 패키지를 찾을 수 있음
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # 런치 파일, URDF, 월드, 브릿지 설정, RViz 설정을 모두 share/my_vehicle/ 아래로 설치
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'urdf'),   glob('urdf/*.xacro') + glob('urdf/*.urdf')),
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*.sdf')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'rviz'),   glob('rviz/*.rviz')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='comsw',
    maintainer_email='comsw@todo.todo',
    description='Automotive SW Programming - Vehicle URDF (Week 3) + Gazebo Simulation (Week 4)',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [],
    },
)
