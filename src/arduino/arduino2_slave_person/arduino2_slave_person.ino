#include <Wire.h>
#include <Arduino.h>   //10-29 추가

// 보행자 신호등 핀 설정

const int CpedGreenLED = 2;   // C 보행자신호 초록불
const int CpedRedLED = 3;     // C 보행자신호 빨간불

const int ApedGreenLED = 4;   // 이하 내용 같음
const int ApedRedLED = 5;
const int BpedGreenLED = 6;
const int BpedRedLED = 7;
const int DpedGreenLED = 8;
const int DpedRedLED = 9;


int phase = 1;
bool isExtended = false;


// const unsigned long delayDuration = 1000; // 2초 지연 시간    10-30 추가



void setup() {
    Wire.begin(8);  // 슬레이브 주소 8
    Wire.onReceive(receiveEvent);
    
  pinMode(CpedGreenLED,OUTPUT);
  pinMode(CpedRedLED,OUTPUT);
  pinMode(ApedGreenLED,OUTPUT);
  pinMode(ApedRedLED,OUTPUT);
  pinMode(BpedGreenLED,OUTPUT);
  pinMode(BpedRedLED,OUTPUT);
  pinMode(DpedGreenLED,OUTPUT);
  pinMode(DpedRedLED,OUTPUT);

    //초기 상태 설정
      digitalWrite(CpedGreenLED, LOW);
      digitalWrite(ApedGreenLED, LOW);
      digitalWrite(BpedGreenLED, LOW);
      digitalWrite(DpedGreenLED, LOW);
      digitalWrite(CpedRedLED, HIGH);
      digitalWrite(ApedRedLED, HIGH);
      digitalWrite(BpedRedLED, HIGH);
      digitalWrite(DpedRedLED, HIGH);




    updatePedestrianLights(phase);
}


void loop() {
    // 대부분의 제어는 I2C 이벤트에서 처리됨
}

void receiveEvent(int bytes) {
    int newPhase = Wire.read();       // I2C로부터 새로운 현시 정보를 수신
    bool newIsExtended = Wire.read(); // I2C로부터 새로운 연장 여부를 수신

        // 연장이 아닌 경우에만 새로운 현시로 업데이트
    if (!newIsExtended) {   // 연장 아닐땐 false를 받아오니까 !false는 true -> 따라서 if문 작동
        phase = newPhase;               // 기존 현시 값을 새로운 현시로 갱신
        updatePedestrianLights(phase);   // 보행자 신호등을 새로운 현시로 업데이트
    }
    
    isExtended = newIsExtended;   // 연장 여부 갱신
}


void updatePedestrianLights(int phase) {

 //     unsigned long currentMillis = millis();
   //   unsigned long lastUpdate = 0;     // 마지막 업데이트 시간      10-30 추가

    // 모든 보행자 신호 초기화
      digitalWrite(CpedGreenLED, LOW);
      digitalWrite(ApedGreenLED, LOW);
      digitalWrite(BpedGreenLED, LOW);
      digitalWrite(DpedGreenLED, LOW);
      digitalWrite(CpedRedLED, HIGH);
      digitalWrite(ApedRedLED, HIGH);
      digitalWrite(BpedRedLED, HIGH);
      digitalWrite(DpedRedLED, HIGH);

    // 신호 초기화를 한 뒤, 2초 지연후 신호 변경
    //if (currentMillis - lastUpdate >= delayDuration) {
    //    lastUpdate = currentMillis;

    // 현시에 따른 보행자 신호 설정
    switch(phase) {
        case 0:  // 차량 황색 2초 동안: 위 초기화 상태(모두 빨강) 유지
            break;
        case 1:  // C , A 보행자 신호 부여
            digitalWrite(CpedGreenLED, HIGH);
            digitalWrite(CpedRedLED, LOW);
            digitalWrite(ApedGreenLED, HIGH);
            digitalWrite(ApedRedLED, LOW);


            break;
            
        case 2:  // 보행자신호 X
 
            break;
            
        case 3:  // B 보행자 신호 부여
            digitalWrite(BpedGreenLED, HIGH);
            digitalWrite(BpedRedLED, LOW);
            break;
            
        case 4:  // D 보행자 신호 부여
            digitalWrite(DpedGreenLED, HIGH);
            digitalWrite(DpedRedLED, LOW);
            break;
    }
  }
