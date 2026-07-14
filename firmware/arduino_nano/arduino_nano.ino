/*
 * Arduino Nano — L298N dual motor driver for conveyor diversion.
 *
 * Commands over USB Serial (9600 baud, newline terminated):
 *   RIGHT  — both motors rotate clockwise (toward e-waste bin)
 *   LEFT   — both motors rotate anticlockwise (toward reject bin)
 *   STOP   — stop immediately
 *   STATUS — report idle/busy
 *
 * Replies: OK | DONE | ERROR
 *
 * Motor: IN1 (D5), IN2 (D6)
 * ENA on L298N should be jumpered to 5V (or hardwired to 5V).
 */

const int PIN_IN1 = 5;
const int PIN_IN2 = 6;

// Configurable run duration
const unsigned long MOTOR_DURATION_MS = 5000;

bool busy = false;
unsigned long motorStopAt = 0;
unsigned long cooldownEndAt = 0; // Cooldown after e-waste detection

void setupPins() {
  pinMode(PIN_IN1, OUTPUT);
  pinMode(PIN_IN2, OUTPUT);
  stopMotors();
}

void stopMotors() {
  digitalWrite(PIN_IN1, LOW);
  digitalWrite(PIN_IN2, LOW);
  busy = false;
}

void driveClockwise() {
  // Clockwise rotation (e-waste detected)
  digitalWrite(PIN_IN1, HIGH);
  digitalWrite(PIN_IN2, LOW);
}

void driveAnticlockwise() {
  // Anticlockwise rotation (reject/non-ewaste)
  digitalWrite(PIN_IN1, LOW);
  digitalWrite(PIN_IN2, HIGH);
}

void startMove(bool right) {
  if (busy) {
    Serial.println("ERROR");
    return;
  }
  // If we are within the 15-second cooldown (5s rotation + 10s scan), reject new signals
  if (millis() < cooldownEndAt) {
    Serial.println("ERROR");
    return;
  }
  
  if (right) {
    driveClockwise();
  } else {
    driveAnticlockwise();
  }
  
  cooldownEndAt = millis() + 15000; // Start 15-second cooldown (5s run + 10s scan)
  busy = true;
  motorStopAt = millis() + MOTOR_DURATION_MS;
  Serial.println("OK");
}

String readCommand() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    cmd.toUpperCase();
    return cmd;
  }
  return "";
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(50); // Set low timeout to keep the loop fast
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
