// Directly compiles BOTH production .ino files; only the hardware APIs are replaced.
#include "stubs/Arduino.h"
#include "stubs/Wire.h"
#include <iostream>
#include <stdexcept>
MockSerial Serial;
MockWire Wire;
uint32_t clockMs = 0;
int activeBoard = 0;
int pins[2][32] = {};
unsigned long millis() { return clockMs; }
void digitalWrite(uint8_t pin, uint8_t value) { pins[activeBoard][pin] = value; }
void pinMode(uint8_t, uint8_t) {}
void noInterrupts() {}
void interrupts() {}
void MockWire::begin() { masterInitialized = true; }
void deliver(const std::vector<uint8_t>& packet) {
  Wire.incoming.assign(packet.begin(), packet.end());
  if (Wire.callback) {
    int previous = activeBoard; activeBoard = 1;
    Wire.callback(int(packet.size())); activeBoard = previous;
  }
}
uint8_t MockWire::endTransmission() {
  ++transmissions;
  if (!masterInitialized || !connected || address != 8) return 2;
  deliver(outgoing); return 0;
}
namespace Car {
#include "../src/arduino/arduino1_car/arduino1_car.ino"
}
namespace Pedestrian {
// Arduino IDE normally inserts these prototypes during sketch preprocessing.
void receiveEvent(int bytes);
void updatePedestrianLights(int phase);
#include "../src/arduino/arduino2_slave_person/arduino2_slave_person.ino"
}
void loops() {
  activeBoard = 0; Car::loop();
  activeBoard = 1; Pedestrian::loop();
}
std::string escape(const std::string& text) {
  std::string result;
  for (char ch : text) {
    if (ch == '\n') result += "\\n";
    else if (ch == '\r') result += "\\r";
    else if (ch == '"' || ch == '\\') { result += '\\'; result += ch; }
    else result += ch;
  }
  return result;
}
void snapshot() {
  std::cout << "{\"ms\":" << clockMs << ",\"phase\":" << Car::phase
    << ",\"state\":\"" << (Car::delayActive ? "YELLOW" : "RUNNING")
    << "\",\"ticks\":" << Car::count
    << ",\"ped_phase\":" << unsigned(Pedestrian::phase)
    << ",\"ped_state\":\"" << (Pedestrian::phase == 0 ? "YELLOW" : "RUNNING")
    << "\",\"fresh\":" << (Car::dataReceived ? "true" : "false")
    << ",\"i2c_count\":" << Wire.transmissions << ",\"car_pins\":[";
  for (int i = 2; i <= 13; ++i) { if (i > 2) std::cout << ','; std::cout << pins[0][i]; }
  std::cout << "],\"ped_pins\":[";
  for (int i = 2; i <= 9; ++i) { if (i > 2) std::cout << ','; std::cout << pins[1][i]; }
  bool presence[12] = {Car::B_st,Car::D_st,Car::B_left,Car::D_left,Car::C_left,Car::C_st,
    Car::A_left,Car::A_st,Car::C_ped,Car::A_ped,Car::B_ped,Car::D_ped};
  std::cout << "],\"presence\":[";
  for (int i = 0; i < 12; ++i) { if (i) std::cout << ','; std::cout << (presence[i] ? "true" : "false"); }
  std::cout << "],\"serial_tx\":\"" << escape(Serial.outgoing) << "\"}" << std::endl;
  Serial.outgoing.clear();
}
std::vector<uint8_t> unhex(const std::string& hex) {
  if (hex.size() % 2) throw std::runtime_error("Odd hex length");
  std::vector<uint8_t> result;
  for (size_t i = 0; i < hex.size(); i += 2)
    result.push_back(uint8_t(std::stoul(hex.substr(i,2),nullptr,16)));
  return result;
}
int main() {
  activeBoard = 1; Pedestrian::setup();
  activeBoard = 0; Car::setup();
  loops(); snapshot();
  std::string line;
  try {
    while (std::getline(std::cin,line)) {
      if (line == "QUIT") break;
      size_t comma = line.find(',');
      std::string command = line.substr(0,comma);
      std::string value = comma == std::string::npos ? "" : line.substr(comma+1);
      if (command == "STEP") {
        uint32_t remaining = uint32_t(std::stoul(value));
        while (remaining) {
          uint32_t delta = remaining > 10 ? 10 : remaining;
          clockMs += delta; remaining -= delta; loops();
        }
      } else if (command == "FRAME") {
        for (uint8_t ch : unhex(value)) Serial.incoming.push_back(char(ch));
        loops();
      } else if (command == "I2C") {
        deliver(unhex(value)); activeBoard = 1; Pedestrian::loop();
      } else if (command == "DISCONNECT") Wire.connected = false;
      else if (command == "RECONNECT") Wire.connected = true;
      else if (command == "SET_CLOCK") { clockMs = uint32_t(std::stoul(value)); loops(); }
      else if (command == "SNAPSHOT") loops();
      else throw std::runtime_error("Unknown command");
      snapshot();
    }
  } catch (const std::exception& error) { std::cerr << error.what(); return 2; }
  return 0;
}
