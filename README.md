# my_vehicle — 오토모티브 SW프로그래밍 실습 (2·3·4·5주차)

주차별 실습을 **하나의 ROS 2 워크스페이스형 저장소**로 정리했습니다. 저장소를 `~/ros2_ws/src`에 clone하면 아래 패키지 3개가 한 번에 빌드됩니다.

- ROS 2 배포판: `lyrical` (Ubuntu 26.04 / WSL2)
- Gazebo Sim: `gz sim` 10.x (`ros-lyrical-ros-gz`)

## 1. 저장소 구조

```
my_vehicle/                     # 저장소 루트 (colcon이 하위 패키지를 자동 탐색)
├── my_vehicle_pkg/             # [2주차] Topic 통신 (publisher / subscriber / launch)
│   ├── my_vehicle_pkg/         #   simple_publisher.py, simple_subscriber.py
│   └── launch/vehicle_demo.launch.py
├── my_vehicle/                 # [3·4주차] URDF/Xacro 차량 + RViz2 + Gazebo + ros_gz_bridge
│   ├── launch/                 #   display.launch.py, spawn_car.launch.py
│   ├── urdf/                   #   vehicle.urdf.xacro, wheel_macro.xacro
│   ├── worlds/car_track.sdf    #   16m x 16m 트랙, 외곽벽, 중앙 분리대, (도전) 15° 경사로
│   ├── config/bridge.yaml      #   /clock, /cmd_vel, /odom, /tf, /joint_states 브릿지
│   └── rviz/display.rviz
├── my_tf_pkg/                  # [5주차] static / dynamic TF 브로드캐스터, TF2 리스너
│   ├── my_tf_pkg/              #   static_tf_broadcaster.py, dynamic_tf_broadcaster.py, tf_listener.py
│   ├── launch/tf_demo.launch.py
│   └── rviz/tf_demo.rviz
└── docs/                       # 실행 결과 캡처
```

## 2. 설치 및 빌드

```bash
sudo apt update
sudo apt install python3-colcon-common-extensions ros-lyrical-ros-gz \
                 ros-lyrical-teleop-twist-keyboard ros-lyrical-joint-state-publisher-gui \
                 ros-lyrical-robot-state-publisher ros-lyrical-xacro ros-lyrical-tf2-tools \
                 liburdfdom-tools graphviz git

mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/ltd9955/my_vehicle.git
cd ~/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

WSL2에서 RViz2/Gazebo 창이 뜨지 않거나 렌더링 에러가 나면 Qt를 X11로 지정합니다.

```bash
echo "export QT_QPA_PLATFORM=xcb" >> ~/.bashrc
```

`--symlink-install`로 빌드하면 RViz2를 종료할 때 나오는 저장 확인 창에서 저장하지 않는 것이 좋습니다. 설정 파일이 소스 폴더의 `.rviz`를 그대로 덮어씁니다.

## 3. 주차별 실행

### 3.1 [2주차] `my_vehicle_pkg` — Topic 통신

```bash
ros2 launch my_vehicle_pkg vehicle_demo.launch.py
```

퍼블리셔가 `/vehicle_status`(std_msgs/String)로 `Vehicle Speed: N km/h`를 1초마다 발행하고, 서브스크라이버가 `Subscribed: ...`로 수신합니다. 두 노드가 실행 중일 때 디스커버리와 QoS를 확인할 수 있습니다.

```bash
ros2 node list
ros2 topic info /vehicle_status --verbose   # Publisher/Subscriber 모두 RELIABLE, VOLATILE, KEEP_LAST(10)
ros2 topic hz /vehicle_status               # 약 1.0 Hz
```

### 3.2 [3주차] `my_vehicle` — RViz2 시각화

```bash
ros2 launch my_vehicle display.launch.py
```

Joint State Publisher 슬라이더를 움직이면 RViz의 조향/바퀴 관절이 따라 움직입니다.

### 3.3 [4주차] `my_vehicle` — Gazebo 시뮬레이션

터미널 1 — Gazebo 기동 + 차량 스폰 + 브릿지:

```bash
ros2 launch my_vehicle spawn_car.launch.py
```

터미널 2 — 키보드 주행 (`i` 전진, `u`/`o` 전진하며 좌/우, `k` 정지):

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

터미널 3 — 오도메트리 / 시계 확인:

```bash
ros2 topic echo /odom --no-arr
ros2 topic hz /clock
```

(도전) `worlds/car_track.sdf` 맨 아래 `ramp_15deg` 모델의 주석을 해제하면 스폰 위치 앞 4 m 지점에 15° 경사로가 생성됩니다. `urdf/wheel_macro.xacro`의 `mu1/mu2`를 바꿔 가며 등판 여부를 비교할 수 있습니다.

![Gazebo 스폰 및 teleop 주행](docs/mission1_2_spawn_and_teleop_drive.png)

### 3.4 [5주차] `my_tf_pkg` — 좌표계와 TF2

```bash
ros2 launch my_tf_pkg tf_demo.launch.py
```

| 노드 | 역할 |
|---|---|
| `static_tf_broadcaster` | `base_link → lidar_link` (x=0.5, z=0.3)를 `/tf_static`으로 1회 발행 |
| `dynamic_tf_broadcaster` | 반지름 2 m 원 궤도 주행에 따른 `odom → base_link`를 `/tf`로 30 Hz 발행 |
| `tf_listener` | 10 Hz로 `odom → lidar_link`를 `lookup_transform`으로 질의해 위치와 Yaw 출력 |
| `rviz2` | Fixed Frame `odom`, TF 디스플레이 (`rviz/tf_demo.rviz`) |

`tf_listener`가 `[TF 룩업 성공] odom -> lidar_link | 위치(...) | 원점거리=2.06m` 를 계속 출력하면 정상입니다.
원점거리 2.06 m는 원 궤도 반지름 2 m와 라이다 오프셋 0.5 m로 계산한 값 √(2² + 0.5²) ≈ 2.06 과 일치합니다.

launch를 켜 둔 채 다른 터미널에서 확인합니다.

```bash
ros2 run tf2_tools view_frames                    # frames_<시각>.pdf 생성
ros2 run tf2_ros tf2_echo odom lidar_link         # 실시간 Translation / Rotation
ros2 topic info /tf_static --verbose              # Durability: TRANSIENT_LOCAL
```

RViz2에서 `odom`, `base_link`, `lidar_link` 좌표축이 보이고, `base_link`가 원을 그리며 이동할 때 `lidar_link`가 앞쪽 오프셋을 유지한 채 함께 회전합니다.

| RViz2 TF 시각화 (1) | RViz2 TF 시각화 (2) |
|---|---|
| ![TF 1](docs/week5_rviz_tf_1.png) | ![TF 2](docs/week5_rviz_tf_2.png) |

| 확인 항목 | 결과 |
|---|---|
| TF 트리 (`docs/week5_frames.pdf`) | `odom → base_link`(30.2 Hz) → `lidar_link`(static), 단절·다중 부모 없음 |
| `tf2_echo odom lidar_link` | Translation, Quaternion, RPY가 원 궤도에 따라 변함 |
| `/tf_static` QoS | Publisher: RELIABLE, TRANSIENT_LOCAL, KEEP_LAST(1) / Subscriber: TRANSIENT_LOCAL |

> `tf_demo.launch.py`는 `odom → base_link`를 발행하므로 4주차 Gazebo(`spawn_car.launch.py`)와 동시에 실행하면 TF가 충돌합니다.

## 4. 원본 코드에서 수정한 내용

### 3·4주차 (code03 + code04 통합)

| 항목 | 원본 | 통합 후 |
|---|---|---|
| 패키지 | `my_vehicle_description`, `my_vehicle_gazebo` 두 개 | `my_vehicle` 하나 |
| URDF 경로 | `spawn_car.launch.py`가 `../code03/urdf/`를 상대 참조 → colcon 설치 후 경로 깨짐 | 자기 패키지 `urdf/` 참조 |
| Gazebo 실행 | `gz` 명령 직접 호출 (`ExecuteProcess`) | `ros_gz_sim/gz_sim.launch.py` include |
| 구동 플러그인 | 없음 (`/cmd_vel`을 보내도 움직이지 않음) | `DiffDrive`(후륜), `JointStatePublisher` 추가 |
| 바퀴 마찰 | 없음 | 바퀴 4개에 `mu1/mu2 = 1.0` |
| `/joint_states` 브릿지 | ROS/Gazebo 토픽 이름이 같아 수신 안 됨 | Gazebo 쪽 `/world/car_track_world/model/auto_vehicle/joint_state`로 매핑 |
| RViz | 설정 없음 | `rviz/display.rviz`로 자동 설정 |
| `setup.py` | `resource/` 항목이 조건부 → ament 인덱스 미등록 가능 | 필수 항목으로 고정, `urdf/`, `rviz/` 설치 추가 |

### 5주차 (code05 → `my_tf_pkg`)

| 항목 | 원본 | 수정 후 |
|---|---|---|
| 패키지명 | launch는 `automotive_tf`, 슬라이드는 `my_tf_pkg` | `my_tf_pkg`로 통일 |
| 실행 파일명 | launch가 `static_tf_broadcaster.py` 처럼 `.py`를 붙여 호출 | `console_scripts` 엔트리포인트 등록, `.py` 제거 |
| launch | RViz2 실행 없음 | `rviz2` 노드와 `tf_demo.rviz` 추가 |
| `tf_listener.py` | `logger.warn()` 사용 → 이 ROS 버전(Python 3.14)에서 `AttributeError`로 노드 종료 | `logger.warning()`으로 변경 |

## 5. 데이터 흐름 (4주차)

```
teleop_twist_keyboard ──/cmd_vel──▶ ros_gz_bridge ──▶ Gazebo DiffDrive ──▶ 후륜 구동
                                                            │
robot_state_publisher ◀──/joint_states── ros_gz_bridge ◀── JointStatePublisher
        │                                                   │
      /tf, /tf_static                    /odom, /tf(odom→base_footprint), /clock
```
