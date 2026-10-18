# YOLOv5–Arduino 신호감응 교차로

웹캠으로 차량·보행자를 감지하고, 구역별 수요에 따라 모형 교차로의 신호 진행 시간을 조절하는 팀 프로젝트입니다. Python이 객체 감지와 ROI 집계를 담당하고, 두 대의 Arduino가 차량·보행자 신호를 제어합니다.

## 시연 영상 — 1현시 최단시간, 최장시간
- [1현시 최단시간 시연](https://youtu.be/1d8LZPIG-BQ)
- [1현시 최단시간 시연2](https://youtu.be/yXnlkb6caIc)

- [1현시 최장시간 시연](https://youtu.be/SIiPOC07tUc)
- [1현시 최장시간 시연2](https://youtu.be/vRZ4VSTkiho)


## 프로젝트 목적과 구조

차량과 보행자가 어느 구역에 있는지 확인해 현재 신호를 유지하거나 다음 현시로 전환합니다. 현시는 교차로에서 동시에 허용하는 차량·보행자 신호의 조합을 뜻합니다.

```text
웹캠 → YOLOv5 객체 감지 → ROI별 존재 여부 집계
                          ↓ USB 직렬 통신
                 차량 Arduino: 시간·현시 제어
                          ↓ I²C
                 보행자 Arduino: 신호 출력
```

- Python: 객체 중심점을 차량 8개·보행자 4개 ROI에 대입해 12개 존재 여부 값을 생성합니다.
- 차량 Arduino: Python 데이터를 받아 현재·다른 현시의 수요를 판단하고 차량 LED와 현시 시간을 제어합니다.
- 보행자 Arduino: 차량 Arduino의 현시 정보를 받아 해당 보행자 LED를 제어합니다.

## 팀 프로젝트에서 맡은 역할

작성자는 **Arduino 차량·보행자 신호 제어와 보드 간 연동**을 담당했습니다.

- 차량·보행자 LED의 핀 설정과 현시별 출력 구성
- 차량·보행자 존재 여부에 따른 신호 유지·종료 조건 구현
- Python에서 받은 12개 데이터를 Arduino 변수로 연결
- `millis()`를 이용한 황색 2초 대기와 현시 전환 처리
- I²C를 통한 차량 보드와 보행자 보드의 현시 연동

팀원은 Python의 YOLOv5 객체 감지와 모델 학습을 담당했습니다. Python이 감지 정보를 제공하고 Arduino가 신호 시간을 결정하는 구조로 연결했습니다.

## 신호 제어 방식

객체 수를 세어 신호 시간을 정하는 대신, 각 ROI에 객체가 있는지를 `0/1`로 전달합니다. 같은 ROI에서 여러 객체가 감지되어도 존재 여부 값은 `1`입니다.

차량 Arduino의 판단 주기는 **5초**입니다. Python의 송신 간격 설정은 0.5초이며, 객체 추론 주기와 Arduino의 신호 판단 주기는 별개입니다.

| 판단 시점 | 조건 | 동작 |
|---|---|---|
| 5·10초 | 현재 현시에 해당하는 차량·보행자 수요 없음 | 현시 종료 시작 |
| 15초 | 다른 현시에 해당하는 수요 있음 | 현시 종료 시작 |
| 20·25초 | 현재 현시 수요가 없거나 다른 현시 수요가 있음 | 현시 종료 시작 |
| 30초 | 최대 진행 시간 도달 | 현시 종료 시작 |
| 현시 종료 후 | 황색 2초 경과 | 다음 현시로 전환 |

다른 현시는 현재 현시를 제외한 모든 현시를 뜻합니다. 20·25초에는 현재 현시의 수요가 계속 있어도 다른 현시의 수요가 있으면 종료합니다.

황색이 시작되면 차량의 초록불을 끄고, 보행자는 모두 빨간불로 전환합니다. `millis()`로 시작 시점을 한 번 저장한 뒤 반복해서 경과 시간을 확인합니다. 2초가 지나면 다음 현시와 보행자 신호를 함께 전달하고, 새 현시의 5초 카운트를 시작합니다.

| 현시 | 차량 신호 | 보행자 초록불 |
|---|---|---|
| 1 | B·D 직진 | C·A |
| 2 | B·D 좌회전 | 없음 |
| 3 | C 직진·좌회전 | B |
| 4 | A 직진·좌회전 | D |

모형 신호등은 초록·황색·빨강 세 개의 LED를 사용합니다. 초록과 황색이 동시에 켜지면 좌회전을, 황색만 켜지면 전환 대기를 표현합니다.

### 통신 형식

Python과 차량 Arduino는 `9600 baud`로 통신합니다. 메시지는 아래 순서의 12개 `0/1` 값이며 쉼표로 구분하고 마지막에 줄바꿈 `\n`을 붙입니다.

```text
B_st,D_st,B_left,D_left,C_left,C_st,A_left,A_st,C_ped,A_ped,B_ped,D_ped
```

차량 Arduino와 보행자 Arduino는 I²C 주소 `8`을 사용합니다. 두 바이트 `[현시, 연장 여부]`를 전달하며, 황색 동안 `[0, 0]`으로 보행자 모두 빨강을 지시하고 전환 완료 후 `[다음 현시, 0]`을 보냅니다.

## 파일 구성

```text
.
├─ README.md
├─ .gitignore
├─ src/
│  ├─ python/
│  │  ├─ detect.py
│  │  └─ signal_control/
│  │     ├─ __init__.py
│  │     ├─ config.py
│  │     ├─ vision.py
│  │     ├─ roi.py
│  │     ├─ protocol.py
│  │     ├─ transport.py
│  │     └─ mock.py
│  ├─ config/
│  │  ├─ signal.json
│  │  └─ mock_scenario.json
│  └─ arduino/
│     ├─ arduino1_car/arduino1_car.ino
│     └─ arduino2_slave_person/arduino2_slave_person.ino
└─ tests/
   ├─ verify.py
   ├─ build_firmware.py
   ├─ test_python.py
   ├─ test_firmware.py
   ├─ firmware_harness.cpp
   └─ stubs/
      ├─ Arduino.h
      └─ Wire.h
```

Python은 `detect.py` 하나에서 시작하며 같은 폴더의 `signal_control` 모듈을 자동으로 불러옵니다. 폴더 구조를 유지해야 설정 파일과 모의 실행 파일의 경로가 맞습니다.

## 실행 방법

### 장비 없이 PC에서 실행

현재 PC 빌드 스크립트는 **Windows, Python 3, MSVC C++ 컴파일러**를 사용합니다. 가중치·웹캠·pySerial은 모의 실행에 필요하지 않습니다. 저장소의 최상위 폴더에서 실행합니다.

```powershell
python -B tests/verify.py --native-only
python -B src/python/detect.py --mode mock
```

첫 명령은 두 Arduino의 실제 `.ino`를 포함한 PC 시험 실행 파일을 빌드하고 테스트합니다. 두 번째 명령은 40초짜리 예시 입력을 재생합니다. 시간·Serial·Wire·GPIO를 모의 API로 대체해 신호 제어 결과를 출력합니다. 결과는 CSV 파일이 아니라 줄마다 JSON 한 개입니다.

### Arduino UNO 컴파일까지 확인

Arduino AVR 코어와 AVR GCC가 기존 Arduino 설치 경로에 준비된 환경에서 실행합니다.

```powershell
python -B tests/verify.py
```

PC 검증과 함께 두 스케치를 UNO/ATmega328P/16MHz 대상으로 컴파일·링크합니다. 이 명령은 보드에 업로드하지 않습니다. 검증 결과는 `build/validation-results.json`에 저장됩니다.

### YOLOv5 모드 실행 조건

YOLO 모드는 학습된 가중치, 호환되는 YOLOv5 코드·라이브러리, 웹캠, 차량 Arduino의 직렬 포트가 필요합니다. 가중치는 아래 설명처럼 현재 유실되어 저장소에 포함하지 않습니다.

설정 파일 [src/config/signal.json](src/config/signal.json)의 경로는 설정 파일이 있는 폴더를 기준으로 해석됩니다.

| 설정 | 참조 위치 |
|---|---|
| `vision.yolo_root` | 저장소 최상위의 `yolov5/` |
| `vision.weights` | 저장소 최상위의 `weights/best.pt` |
| `classes.vehicle_ids` | 예시 차량 클래스 `[0]` |
| `classes.pedestrian_ids` | 예시 보행자 클래스 `[1]` |

외부 YOLOv5 코드에는 `models/common.py`, `utils/dataloaders.py`, `utils/general.py`, `utils/torch_utils.py`가 필요합니다. 해당 코드의 의존성과 pySerial을 준비하고 모델·클래스·ROI·포트를 맞춘 뒤 실행합니다. `COM3`는 포트 이름의 예시입니다.

```powershell
python -m pip install pyserial
python -m pip install -r yolov5/requirements.txt
python -B src/python/detect.py --mode yolo --port COM3 --preview
```

## 코드 검증 결과

GitHub 업로드용 폴더에서 PC 시험 실행 파일과 UNO 두 스케치를 빌드하고, 다음 항목을 확인했습니다.

| 검증 항목 | 결과 |
|---|---|
| Python 문법 | 실행·검증 파일 12개 통과 |
| Python 테스트 | 12개 통과 |
| Arduino PC 테스트 | 11개 통과(20·25초의 늦은 차량·보행자 수요 16사례 포함) |
| 직렬 메시지 12개 필드 | 해당 Arduino 변수와 일치 |
| 현시 `1 → 2 → 3 → 4 → 1` | 순환·보행자 매핑 통과 |
| 황색 대기 | 1999ms 유지, 2000ms 전환 확인 |
| 감응 조건 | 현재 수요·15·20·25초의 다른 현시 수요·30초 상한 확인 |
| UNO 컴파일·링크 | 차량·보행자 모두 통과 |
| 기본 모의 실행 | 40초 정상 종료 |

전체 23개 테스트에서 실패·오류·생략은 0입니다. 실제 두 Arduino 코드를 PC 하네스에 포함하므로 시험을 위해 신호 알고리즘을 별도로 작성하지 않습니다.

Python은 현재 Arduino의 일반 로그를 상태 표시로 변환하지 않습니다. Arduino에는 입력 만료를 판정하는 타임아웃 처리가 없습니다. 실제 UART·I²C 지연과 웹캠·LED 동작은 PC 검증에 포함되지 않습니다.

## 가중치 유실과 현재 설정

프로젝트에서 사용한 **YOLOv5 학습 가중치와 학습 자료가 유실**되어 가중치 파일은 포함하지 않습니다. 코드에서는 `weights/best.pt`를 참조하도록 설정했으며, 파일이 없으면 YOLO 모드에서 누락된 경로를 안내합니다. `best.pt`는 현재 코드의 예시 파일명입니다.

현재 클래스 번호와 네 보행자 ROI도 시뮬레이션용 예시값입니다. 보행자 ROI는 640×480 화면을 기준으로 설정했습니다. 실제 모델과 카메라를 연결할 때는 모델의 클래스 순서와 영상 좌표에 맞춰 조정해야 합니다.

가중치가 없어 실제 YOLO 모델 로드·인식 정확도는 이번 코드 검증에서 확인하지 않았습니다. PC 모의 실행으로 ROI·통신·신호 제어를 확인할 수 있습니다.
