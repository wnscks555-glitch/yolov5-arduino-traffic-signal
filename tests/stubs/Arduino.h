#ifndef RECOVERY_TEST_ARDUINO_H
#define RECOVERY_TEST_ARDUINO_H
#include <stdint.h>
#include <deque>
#include <sstream>
#include <string>
#include <cstdlib>
#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define F(value) value
unsigned long millis();
void digitalWrite(uint8_t pin, uint8_t value);
void pinMode(uint8_t pin, uint8_t mode);
void noInterrupts();
void interrupts();
// Only the String operations used by the preserved original sketch.
class String {
 public:
  String() {}
  String(const std::string& value) : value_(value) {}
  String(const char* value) : value_(value) {}
  int indexOf(char ch, unsigned int from = 0) const {
    size_t index = value_.find(ch, from);
    return index == std::string::npos ? -1 : int(index);
  }
  String substring(unsigned int from, unsigned int to) const {
    if (from > to) { unsigned int temp = from; from = to; to = temp; }
    if (from >= value_.size()) return String();
    if (to > value_.size()) to = unsigned(value_.size());
    return String(value_.substr(from, to - from));
  }
  String substring(unsigned int from) const { return substring(from, unsigned(value_.size())); }
  long toInt() const { return std::strtol(value_.c_str(), nullptr, 10); }
  const std::string& text() const { return value_; }
 private:
  std::string value_;
};
struct MockSerial {
  std::deque<char> incoming;
  std::string outgoing;
  void begin(unsigned long) {}
  int available() { return int(incoming.size()); }
  int read() { char ch = incoming.front(); incoming.pop_front(); return uint8_t(ch); }
  String readStringUntil(char delimiter) {
    std::string result;
    while (!incoming.empty()) {
      char ch = incoming.front(); incoming.pop_front();
      if (ch == delimiter) break;
      result += ch;
    }
    return String(result);
  }
  void print(const String& value) { outgoing += value.text(); }
  void print(const char* value) { outgoing += value; }
  void print(char value) { outgoing += value; }
  void print(uint8_t value) { outgoing += std::to_string(unsigned(value)); }
  template<typename T> void print(T value) { outgoing += std::to_string(value); }
  template<typename T> void println(T value) { print(value); outgoing += "\r\n"; }
};
extern MockSerial Serial;
#endif
