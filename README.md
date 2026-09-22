# my_vehicle — 오토모티브 SW프로그래밍 4주차 과제

3주차(`code03`, URDF/Xacro 차량 모델 + RViz2 시각화)와 4주차(`code04`, Gazebo Sim 월드 + ros_gz_bridge)를
**하나의 ROS 2 패키지 `my_vehicle`** 로 통합한 저장소입니다.

- ROS 2 배포판: `lyrical` (Ubuntu / WSL2)
- Gazebo Sim: `gz sim` 10.x (`ros-lyrical-ros-gz` vendor 패키지)

## 1. 패키지 구조

```
my_vehicle/
├── package.xml
├── setup.py                 # launch/urdf/worlds/config/rviz 를 share/ 로 설치
├── setup.cfg
├── resource/my_vehicle
├── my_vehicle/__init__.py
├── launch/
│   ├── display.launch.py    # [3주차] robot_state_publisher + joint_state_publisher_gui + RViz2
│   └── spawn_car.launch.py  # [4주차] Gazebo Sim + 차량 스폰 + ros_gz_bridge + robot_state_publisher
├── urdf/
│   ├── vehicle.urdf.xacro   # 4륜 차량 (섀시 + 전륜 조향 + 후륜 구동) + Gazebo DiffDrive 플러그인
│   └── wheel_macro.xacro    # 바퀴 매크로 (관성, 마찰계수 mu1/mu2)
├── worlds/
│   └── car_track.sdf        # 16m x 16m 트랙, 외곽벽 4개, 중앙 분리대, (도전) 15° 경사로
├── config/
│   └── bridge.yaml          # /clock, /cmd_vel, /odom, /tf, /joint_states 브릿지 매핑
└── rviz/
    └── display.rviz         # Fixed Frame=base_link, RobotModel 포함 RViz 설정
```

## 2. 통합하면서 수정한 내용

| 항목 | 원본 (code03 / code04) | 통합 후 |
|---|---|---|
| 패키지 | `my_vehicle_description`, `my_vehicle_gazebo` 두 개 | `my_vehicle` 하나 |
| URDF 경로 | `spawn_car.launch.py`가 `../code03/urdf/`를 상대 참조 → colcon 설치 후 경로 깨짐 | 자기 패키지 `urdf/` 참조 (소스/설치 어디서든 동작) |
| Gazebo 실행 | `gz` 명령 직접 호출 (`ExecuteProcess`) → vendor 설치 시 PATH 문제 | `ros_gz_sim/gz_sim.launch.py` include |
| 구동 플러그인 | 없음 (`/cmd_vel` 보내도 움직이지 않음) | `gz::sim::systems::DiffDrive` (후륜), `JointStatePublisher` 추가 |
| 바퀴 마찰 | 없음 | 바퀴 4개에 `mu1/mu2 = 1.0` |
| `/joint_states` 브릿지 | ROS/Gazebo 토픽 이름 동일 → 수신 안 됨 | Gazebo 쪽 `/world/car_track_world/model/auto_vehicle/joint_state` 로 매핑 |
| RViz | 설정 없음 (Fixed Frame `map` 경고, RobotModel 수동 추가 필요) | `rviz/display.rviz` 로 자동 설정 |
| `setup.py` | `resource/` 항목이 조건부 → ament 인덱스 미등록 가능 | 필수 항목으로 고정, `urdf/`, `rviz/` 설치 추가 |

## 3. 설치 및 빌드

```bash
sudo apt update
sudo apt install ros-$ROS_DISTRO-ros-gz ros-$ROS_DISTRO-teleop-twist-keyboard \
                 ros-$ROS_DISTRO-joint-state-publisher-gui ros-$ROS_DISTRO-robot-state-publisher \
                 ros-$ROS_DISTRO-xacro

mkdir -p ~/ros2_ws/src && cd ~/ros2_ws/src
git clone https://github.com/<GITHUB_ID>/my_vehicle.git
cd ~/ros2_ws
colcon build --packages-select my_vehicle --symlink-install
source install/setup.bash
```

## 4. 실행

### 4.1 [3주차] RViz2 시각화

```bash
ros2 launch my_vehicle display.launch.py
```

Joint State Publisher 슬라이더를 움직이면 RViz의 조향/바퀴 관절이 따라 움직입니다.

### 4.2 [4주차] Gazebo 시뮬레이션

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

### 4.3 (도전) 15° 경사로

`worlds/car_track.sdf` 맨 아래 `ramp_15deg` 모델의 주석(`<!-- -->`)을 해제하면
스폰 위치 앞 4 m 지점에 경사로가 생성됩니다. `urdf/wheel_macro.xacro`의 `mu1/mu2` 값을
바꿔 가며 등판 성공 여부를 비교할 수 있습니다.

## 5. 실습 결과

| 미션 | 내용 | 결과 |
|---|---|---|
| 1 | Gazebo 트랙에 4륜 차량 스폰 | `docs/mission1_spawn.png` |
| 2 | teleop S자 주행 + `/odom` 출력 | `docs/mission2_odom.png` |
| 3 | `ros2 topic hz /clock` + RTF | `docs/mission3_clock_rtf.png` |
| 4 (도전) | 15° 경사로 등판 | `docs/mission4_ramp.png` |

> 스크린샷은 `docs/` 폴더에 넣고 위 파일명을 맞춰 주세요.

## 6. 데이터 흐름

```
teleop_twist_keyboard ──/cmd_vel──▶ ros_gz_bridge ──▶ Gazebo DiffDrive ──▶ 후륜 구동
                                                            │
robot_state_publisher ◀──/joint_states── ros_gz_bridge ◀── JointStatePublisher
        │                                                   │
      /tf, /tf_static                    /odom, /tf(odom→base_footprint), /clock
```
