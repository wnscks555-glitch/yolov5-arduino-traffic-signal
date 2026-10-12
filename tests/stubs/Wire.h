#ifndef RECOVERY_TEST_WIRE_H
#define RECOVERY_TEST_WIRE_H
#include "Arduino.h"
#include <vector>
#define WIRE_HAS_TIMEOUT 1
struct MockWire {
  std::vector<uint8_t> outgoing;
  std::deque<uint8_t> incoming;
  void (*callback)(int) = nullptr;
  bool masterInitialized = false, connected = true;
  uint32_t timeout = 0;
  uint8_t address = 0;
  unsigned transmissions = 0;
  void begin();
  void begin(uint8_t slave) { address = slave; }
  void setWireTimeout(uint32_t value, bool) { timeout = value; }
  void onReceive(void (*handler)(int)) { callback = handler; }
  void beginTransmission(uint8_t slave) { address = slave; outgoing.clear(); }
  void write(uint8_t value) { outgoing.push_back(value); }
  uint8_t endTransmission();
  int available() { return int(incoming.size()); }
  int read() { if (incoming.empty()) return -1; uint8_t value = incoming.front(); incoming.pop_front(); return value; }
};
extern MockWire Wire;
#endif
