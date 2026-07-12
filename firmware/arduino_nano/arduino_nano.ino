/*
 * Arduino Nano — L298N dual motor driver for conveyor diversion.
 *
 * Commands over USB Serial (9600 baud, newline terminated):
 *   RIGHT  — both motors rotate toward e-waste bin
 *   LEFT   — both motors rotate toward reject bin
 *   STOP   — stop immediately
 *   STATUS — report idle/busy
 *
 * Replies: OK | DONE | ERROR
 *
 * Motor A: IN1, IN2, ENA (PWM)
 * Motor B: IN3, IN4, ENB (PWM)
 * Both motors always rotate together.
 */

const int PIN_IN1 = 2;
const int PIN_IN2 = 3;
const int PIN_IN3 = 4;
const int PIN_IN4 = 5;
const int PIN_ENA = 9;   // PWM
const int PIN_ENB = 10;  // PWM

// Configurable run duration and PWM speed
const unsigned long MOTOR_DURATION_MS = 1500;
const int MOTOR_SPEED = 200;  // 0-255

bool busy = false;
unsigned long motorStopAt = 0;

void setupPins() {
  pinMode(PIN_IN1, OUTPUT);
  pinMode(PIN_IN2, OUTPUT);
  pinMode(PIN_IN3, OUTPUT);
  pinMode(PIN_IN4, OUTPUT);
  pinMode(PIN_ENA, OUTPUT);
  pinMode(PIN_ENB, OUTPUT);
  stopMotors();
}

void stopMotors() {
  digitalWrite(PIN_IN1, LOW);
  digitalWrite(PIN_IN2, LOW);
  digitalWrite(PIN_IN3, LOW);
  digitalWrite(PIN_IN4, LOW);
  analogWrite(PIN_ENA, 0);
  analogWrite(PIN_ENB, 0);
  busy = false;
}

void driveForward() {
  // Direction A and B identical (conveyor)
  digitalWrite(PIN_IN1, HIGH);
  digitalWrite(PIN_IN2, LOW);
  digitalWrite(PIN_IN3, HIGH);
  digitalWrite(PIN_IN4, LOW);
  analogWrite(PIN_ENA, MOTOR_SPEED);
  analogWrite(PIN_ENB, MOTOR_SPEED);
}

void driveReverse() {
  digitalWrite(PIN_IN1, LOW);
  digitalWrite(PIN_IN2, HIGH);
  digitalWrite(PIN_IN3, LOW);
  digitalWrite(PIN_IN4, HIGH);
  analogWrite(PIN_ENA, MOTOR_SPEED);
  analogWrite(PIN_ENB, MOTOR_SPEED);
}

void startMove(bool right) {
  if (busy) {
    Serial.println("ERROR");
    return;
  }
  if (right) {
    driveForward();
  } else {
    driveReverse();
  }
  busy = true;
  motorStopAt = millis() + MOTOR_DURATION_MS;
  Serial.println("OK");
}

String readCommand() {
  static String buffer;
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (buffer.length() > 0) {
        String cmd = buffer;
        buffer = "";
        cmd.trim();
        cmd.toUpperCase();
        return cmd;
      }
    } else {
      buffer += c;
      if (buffer.length() > 32) {
        buffer = "";
      }
    }
  }
  return "";
}

void setup() {
  Serial.begin(9600);
  setupPins();
  Serial.println("OK");
}

void loop() {
  if (busy && millis() >= motorStopAt) {
    stopMotors();
    Serial.println("DONE");
  }

  String cmd = readCommand();
  if (cmd.length() == 0) {
    return;
  }

  if (cmd == "RIGHT") {
    startMove(true);
  } else if (cmd == "LEFT") {
    startMove(false);
  } else if (cmd == "STOP") {
    stopMotors();
    Serial.println("OK");
  } else if (cmd == "STATUS") {
    Serial.println(busy ? "OK" : "OK");
  } else {
    Serial.println("ERROR");
  }
}
