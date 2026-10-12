#include <Wire.h>
#include <Arduino.h>   //10-29 추가
// 차량 신호등 핀 설정
const int BGreenLED = 2;
const int BYellowLED = 3;
const int BRedLED = 4;
const int DGreenLED = 5;
const int DYellowLED = 6;
const int DRedLED = 7;
const int CGreenLED = 8;
const int CYellowLED = 9;
const int CRedLED = 10;
const int AGreenLED = 11;
const int AYellowLED = 12;
const int ARedLED = 13;

// 차량 상태 변수
bool A_st = false;
bool B_st = false;
bool C_st = false;
bool D_st = false;
bool A_left = false;
bool B_left = false;
bool C_left = false;
bool D_left = false;
// 보행자 상태 변수 10-30
bool C_ped = false;
bool A_ped = false;
bool B_ped = false;
bool D_ped = false;



bool dataReceived = false;  // 데이터 수신 여부를 추적하는 변수

// 타이머
unsigned long previousMillis;
unsigned long currentMillis;
unsigned long AMillis;
unsigned long BMillis;
bool delayActive = false;  // 황색 전환 중인지 확인: 시작 시간은 한 번만 저장
unsigned long lastPhaseChangeTime = 0; // 마지막 현시 변경 시간을 저장  10-30
const unsigned long delayDuration = 2000; // 황색불 신호 2초 지연 시간 설정   10-30

const unsigned long interval = 5000;
int count = 0;
int phase = 1;



// 아두이노2로 정보 송신 코드
void sendPhaseToSlave(int phase, bool isExtended) {
    Wire.beginTransmission(8);  // 슬레이브 주소 8
    Wire.write(phase);   // 현재 현시 전송
    Wire.write(isExtended);     // 연장 여부 전송
    
    int error = Wire.endTransmission();  // 전송 종료 및 오류 코드 반환
    if (error != 0) {
        Serial.print("I2C 전송 오류 코드: ");
        Serial.println(error);
    } else {
        Serial.println("I2C 전송 성공");
    }
}
// 1현시 신호 활성화 함수
void activatePhase1() {
    digitalWrite(BGreenLED, HIGH); 
    digitalWrite(DGreenLED, HIGH);
    digitalWrite(CRedLED, HIGH);
    digitalWrite(ARedLED, HIGH);     
    digitalWrite(BRedLED, LOW);
    digitalWrite(DRedLED, LOW);    
}

// 2현시 신호 활성화 함수
void activatePhase2() {
    digitalWrite(BGreenLED, HIGH); 
    digitalWrite(DGreenLED, HIGH);
    digitalWrite(BYellowLED, HIGH); 
    digitalWrite(DYellowLED, HIGH);
    digitalWrite(BRedLED, LOW); 
    digitalWrite(DRedLED, LOW);    
    digitalWrite(CRedLED, HIGH); 
    digitalWrite(ARedLED, HIGH);   
    digitalWrite(CYellowLED, LOW); 
    digitalWrite(AYellowLED, LOW);

}

// 3현시 신호 활성화 함수
void activatePhase3() {

    digitalWrite(CGreenLED, HIGH);
    digitalWrite(CYellowLED, HIGH);
    digitalWrite(ARedLED, HIGH); 
    digitalWrite(BRedLED, HIGH);    
    digitalWrite(CRedLED, LOW); 
    digitalWrite(DRedLED, HIGH);
    digitalWrite(AYellowLED, LOW); 
    digitalWrite(BYellowLED, LOW);   
    digitalWrite(DYellowLED, LOW);
    digitalWrite(BGreenLED, LOW); 
    digitalWrite(AGreenLED, LOW);   
    digitalWrite(DGreenLED, LOW);
}

// 4현시 신호 활성화 함수
void activatePhase4() {
    digitalWrite(AGreenLED, HIGH);
    digitalWrite(AYellowLED, HIGH);
    digitalWrite(ARedLED, LOW); 
    digitalWrite(BRedLED, HIGH);    
    digitalWrite(CRedLED, HIGH); 
    digitalWrite(DRedLED, HIGH);
    digitalWrite(BYellowLED, LOW); 
    digitalWrite(CYellowLED, LOW);   
    digitalWrite(DYellowLED, LOW);
    digitalWrite(BGreenLED, LOW); 
    digitalWrite(CGreenLED, LOW);   
    digitalWrite(DGreenLED, LOW);
}

// 데이터 파싱 함수 (직진 및 좌회전 차량 정보 포함)
void parseData(String data) {
    int commaIndex = 0;
    int valueIndex = 0;

// Python 코드의 전송 순서에 맞춰 B_st, D_st부터 시작    10-29 수정

  ///////////////////////////// B,D 직진, 좌회전 차량 감지 /////////////////////////////////
    commaIndex = data.indexOf(',');
    B_st = data.substring(0, commaIndex).toInt();
    valueIndex = commaIndex + 1;

    commaIndex = data.indexOf(',', valueIndex);
    D_st = data.substring(valueIndex, commaIndex).toInt();
    valueIndex = commaIndex + 1;

    commaIndex = data.indexOf(',', valueIndex);
    B_left = data.substring(valueIndex, commaIndex).toInt();
    valueIndex = commaIndex + 1;

    commaIndex = data.indexOf(',', valueIndex);
    D_left = data.substring(valueIndex, commaIndex).toInt();
    valueIndex = commaIndex + 1;



  ///////////////////////////// C,A 직진, 좌회전 차량 감지 /////////////////////////////////
    commaIndex = data.indexOf(',', valueIndex);
    C_left = data.substring(valueIndex, commaIndex).toInt();
    valueIndex = commaIndex + 1;

    commaIndex = data.indexOf(',', valueIndex);
    C_st = data.substring(valueIndex, commaIndex).toInt();
    valueIndex = commaIndex + 1;

    commaIndex = data.indexOf(',', valueIndex);
    A_left = data.substring(valueIndex, commaIndex).toInt();
    valueIndex = commaIndex + 1;

    commaIndex = data.indexOf(',', valueIndex);
    A_st = data.substring(valueIndex, commaIndex).toInt();
    valueIndex = commaIndex + 1;

  ///////////////////////////// 보행자 감지 /////////////////////////////////    
    commaIndex = data.indexOf(',', valueIndex);
    C_ped = data.substring(valueIndex, commaIndex).toInt();
    valueIndex = commaIndex + 1;

    commaIndex = data.indexOf(',', valueIndex);
    A_ped = data.substring(valueIndex, commaIndex).toInt();
    valueIndex = commaIndex + 1;

    commaIndex = data.indexOf(',', valueIndex);
    B_ped = data.substring(valueIndex, commaIndex).toInt();
    valueIndex = commaIndex + 1;

    D_ped = data.substring(valueIndex).toInt();     // 마지막 데이터 할당 (D 보행자)




}

// 현재 현시에 차량이 있는지 확인하는 함수
bool hasCurrentPhaseTraffic(int phase) {
  
      // 데이터가 수신되지 않았을 경우 false 반환
    if (!dataReceived) {
        return false;
    }

    switch (phase) {
        case 1:
            return B_st || D_st || C_ped || A_ped;    // BD직진 , CA 보행자
        case 2:
            return B_left || D_left;  // BD 좌회전, 보행자 X
        case 3:
            return C_st || C_left || B_ped;  // C 직좌, B 보행자
        case 4:
            return A_st || A_left || D_ped;  // A 직좌, D 보행자
        default:
            return false;
   
        
    }
}
bool hasNextPhaseTraffic(int phase) {
  
      // 데이터가 수신되지 않았을 경우 false 반환
    if (!dataReceived) {
        return false;
    }

    switch (phase) {
        case 1:
            return B_left || D_left || C_st || C_left || A_st || A_left || B_ped || D_ped;;               
        case 2:
            return C_st || C_left || A_st || A_left || B_st || D_st || A_ped || B_ped || C_ped || D_ped;
        case 3:
            return A_st || A_left || B_st || D_st || B_left || D_left || A_ped || C_ped || D_ped;
        case 4:
            return B_st || D_st ||  B_left || D_left || C_st || C_left || A_ped || B_ped || C_ped;
        default:
            return false;
   
        
    }
}

// 현시 종료 시 황색 불을 키고 다음 현시로 전환하는 함수
void endPhase(int &phase) {    // <<< int phase 하면 phase 값이 업데이트가 안되서 갇혀버림. &phase를 해야함
    currentMillis = millis();  // 수신 처리 후의 최신 시간으로 2초 경과 확인
    AMillis = currentMillis;
    switch (phase) {
        case 1:
            // 황색 시작: 처음 들어왔을 때만 실행
            if (!delayActive) {
                digitalWrite(BGreenLED, LOW); digitalWrite(DGreenLED, LOW);
                digitalWrite(BYellowLED, HIGH); digitalWrite(DYellowLED, HIGH);
                lastPhaseChangeTime = currentMillis;
                delayActive = true;
                sendPhaseToSlave(0, false);  // 황색 중 보행자 모두 빨강
            }

            // 다음 loop에서도 확인하며, 2초가 지난 뒤에만 전환 완료
            if (currentMillis - lastPhaseChangeTime >= delayDuration) {
                digitalWrite(BGreenLED, HIGH); digitalWrite(DGreenLED, HIGH);

                // 카운트 초기화 및 다음 현시로 변경
                count = 0;
                phase++;
                if (phase > 4) {
                    phase = 1;
                }
                dataReceived = false;

                Serial.print("다음 현시로 전환: ");
                Serial.println(phase);
                BMillis = AMillis;   // 현시 시간 초기화: 기존 변수 유지
                previousMillis = currentMillis;  // 새 현시부터 5초 카운트 시작
                delayActive = false;
                sendPhaseToSlave(phase, false);  // 완료 후에만 다음 현시 전달
            }
            break;  // 2초 전에도 다음 case로 넘어가지 않도록 if 밖에 둠

        case 2:
            // 황색 시작: 처음 들어왔을 때만 실행
            if (!delayActive) {
                digitalWrite(BGreenLED, LOW); digitalWrite(DGreenLED, LOW);
                lastPhaseChangeTime = currentMillis;
                delayActive = true;
                sendPhaseToSlave(0, false);  // 황색 중 보행자 모두 빨강
            }

            // 다음 loop에서도 확인하며, 2초가 지난 뒤에만 전환 완료
            if (currentMillis - lastPhaseChangeTime >= delayDuration) {
                digitalWrite(BYellowLED, LOW); digitalWrite(DYellowLED, LOW);
                digitalWrite(BRedLED, HIGH); digitalWrite(DRedLED, HIGH);

                // 카운트 초기화 및 다음 현시로 변경
                count = 0;
                phase++;
                if (phase > 4) {
                    phase = 1;
                }
                dataReceived = false;

                Serial.print("다음 현시로 전환: ");
                Serial.println(phase);
                BMillis = AMillis;   // 현시 시간 초기화: 기존 변수 유지
                previousMillis = currentMillis;  // 새 현시부터 5초 카운트 시작
                delayActive = false;
                sendPhaseToSlave(phase, false);  // 완료 후에만 다음 현시 전달
            }
            break;  // 2초 전에도 다음 case로 넘어가지 않도록 if 밖에 둠

        case 3:
            // 황색 시작: 처음 들어왔을 때만 실행
            if (!delayActive) {
                digitalWrite(CGreenLED, LOW);
                lastPhaseChangeTime = currentMillis;
                delayActive = true;
                sendPhaseToSlave(0, false);  // 황색 중 보행자 모두 빨강
            }

            // 다음 loop에서도 확인하며, 2초가 지난 뒤에만 전환 완료
            if (currentMillis - lastPhaseChangeTime >= delayDuration) {
                digitalWrite(CYellowLED, LOW);
                digitalWrite(CRedLED, HIGH);

                // 카운트 초기화 및 다음 현시로 변경
                count = 0;
                phase++;
                if (phase > 4) {
                    phase = 1;
                }
                dataReceived = false;

                Serial.print("다음 현시로 전환: ");
                Serial.println(phase);
                BMillis = AMillis;   // 현시 시간 초기화: 기존 변수 유지
                previousMillis = currentMillis;  // 새 현시부터 5초 카운트 시작
                delayActive = false;
                sendPhaseToSlave(phase, false);  // 완료 후에만 다음 현시 전달
            }
            break;  // 2초 전에도 다음 case로 넘어가지 않도록 if 밖에 둠

        case 4:
            // 황색 시작: 처음 들어왔을 때만 실행
            if (!delayActive) {
                digitalWrite(AGreenLED, LOW);
                lastPhaseChangeTime = currentMillis;
                delayActive = true;
                sendPhaseToSlave(0, false);  // 황색 중 보행자 모두 빨강
            }

            // 다음 loop에서도 확인하며, 2초가 지난 뒤에만 전환 완료
            if (currentMillis - lastPhaseChangeTime >= delayDuration) {
                digitalWrite(AYellowLED, LOW);
                digitalWrite(ARedLED, HIGH);

                // 카운트 초기화 및 다음 현시로 변경
                count = 0;
                phase++;
                if (phase > 4) {
                    phase = 1;
                }
                dataReceived = false;

                Serial.print("다음 현시로 전환: ");
                Serial.println(phase);
                BMillis = AMillis;   // 현시 시간 초기화: 기존 변수 유지
                previousMillis = currentMillis;  // 새 현시부터 5초 카운트 시작
                delayActive = false;
                sendPhaseToSlave(phase, false);  // 완료 후에만 다음 현시 전달
            }
            break;  // 2초 전에도 다음 case로 넘어가지 않도록 if 밖에 둠

    }
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

void setup() {
  
  Serial.begin(9600);  // 시리얼 통신 시작
  Wire.begin();  // 차량 보드를 I2C 마스터로 초기화

  pinMode(BGreenLED,OUTPUT);
  pinMode(BYellowLED,OUTPUT);
  pinMode(BRedLED,OUTPUT);
  pinMode(DGreenLED,OUTPUT);
  pinMode(DYellowLED,OUTPUT);
  pinMode(DRedLED,OUTPUT);
  pinMode(CGreenLED,OUTPUT);
  pinMode(CYellowLED,OUTPUT);
  pinMode(CRedLED,OUTPUT);
  pinMode(AGreenLED,OUTPUT);
  pinMode(AYellowLED,OUTPUT);
  pinMode(ARedLED,OUTPUT);

  digitalWrite(BGreenLED,LOW);
  digitalWrite(BYellowLED,LOW);
  digitalWrite(BRedLED,HIGH);
  digitalWrite(DGreenLED,LOW);
  digitalWrite(DYellowLED,LOW);
  digitalWrite(DRedLED,HIGH);
  digitalWrite(CGreenLED,LOW);
  digitalWrite(CYellowLED,LOW);
  digitalWrite(CRedLED,HIGH);
  digitalWrite(AGreenLED,LOW);
  digitalWrite(AYellowLED,LOW);
  digitalWrite(ARedLED,HIGH);


//  activatePhase1();  // 1현시 신호를 기본으로 활성화

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


}

void loop() {

    currentMillis = millis();
    AMillis = millis();

    
    // python으로부터 차량 데이터를 수신
    if (Serial.available()) {
        String data = Serial.readStringUntil('\n');
        parseData(data);  // 데이터 파싱하여 상태 업데이트
        dataReceived = true;  // 데이터가 수신되었음을 표시
        Serial.println("차량 데이터를 제공받았습니다.:"); // 데이터 수신 확인 메시지
        Serial.println(data);  // 수신한 데이터를 출력
    }

    // 황색 중에는 수신 후 2초 경과만 확인하고 기존 Green/카운트 처리를 건너뜀
    if (delayActive) {
        endPhase(phase);
        return;
    }

            // 각 현시에 따라 신호등 제어     // 10-30 millis 카운트 반복문 밖으로 꺼냄 - 반복문 안에 있는거.. 이게 에러의 원인이었나?
            if(phase>0){    // switch문 break 할때 loop 초기화 방지 (처음으로 돌아가버림)
              switch (phase) {
                case 1:
                    activatePhase1();
                    break;
                case 2:
                    activatePhase2();
                    break;
                case 3:
                    activatePhase3();
                    break;
                case 4:
                    activatePhase4();
                    break;
              }
            }
   
        

          if (currentMillis - previousMillis >= interval) {  // 5초 마다 카운트
              previousMillis = currentMillis;
              count++;

          // {  previousMillis = currentMillis;      // 이전시간 초기화     10-29 15:15
          //    delay(5000);  // 초기 신호 5초 대기

         // {   delay(3000); //3초마다 카운트 
           //   count++;

           // Python으로 전송할 데이터 송신 (파이썬에서 수신 및 출력 처리)
             // 각각의 정보를 개별적으로 출력
            Serial.print("현재 현시 시간 경과: ");
            Serial.print((AMillis - BMillis) / 1000);  // After 시간와 Before 시간 차이 = 현재 현시 시간
            Serial.print("초");
            Serial.print(", 카운트: ");
            Serial.print(count);
            Serial.print(", 현재 현시: ");
            Serial.println(phase);



             if ((count == 3 && hasNextPhaseTraffic(phase)) ||   // 3카운트일때 현재 현시 제외한, 나머지 현시에 차량or보행자 있을때 pass
               ((count == 1 || count == 2 || count == 4 || count == 5) && !hasCurrentPhaseTraffic(phase))) { // 현재 현시에 차량or보행자 없을시 pass
               endPhase(phase); // 현시 종료 시 황색불 처리
            }
              }  else {
                // 현시가 연장될 때 아두이노2 슬레이브로 전송
                sendPhaseToSlave(phase, true);
              }

          
              if (count == 6) {
                endPhase(phase); // 현시 종료 시 황색불 처리
            } 
        }
    




////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////



