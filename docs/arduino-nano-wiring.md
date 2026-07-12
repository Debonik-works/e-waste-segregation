# Arduino Nano wiring guide

Firmware: [`firmware/arduino_nano/arduino_nano.ino`](../firmware/arduino_nano/arduino_nano.ino)

## Role

Receives `RIGHT` / `LEFT` / `STOP` / `STATUS` over USB Serial and drives **two** DC geared motors together via L298N.

## Pin map (default sketch)

| Nano pin | L298N | Function |
|----------|-------|----------|
| D2 | IN1 | Motor A direction |
| D3 | IN2 | Motor A direction |
| D4 | IN3 | Motor B direction |
| D5 | IN4 | Motor B direction |
| D9 (PWM) | ENA | Motor A speed |
| D10 (PWM) | ENB | Motor B speed |
| GND | GND | Common ground |
| 5V | 5V logic (if needed) | Logic supply (see L298N doc) |

Motor power (VMOT) comes from a **separate** battery/PSU — do not power motors from Nano 5V.

## Serial protocol

- Baud: **9600**
- Commands: newline-terminated ASCII `RIGHT`, `LEFT`, `STOP`, `STATUS`
- Replies: `OK`, `DONE`, `ERROR`

`RIGHT` / `LEFT` run for `MOTOR_DURATION_MS` (default 1500), then auto-stop and print `DONE`.

## USB connection

See [usb-serial.md](usb-serial.md). The Nano appears as a COM port (Windows) or `/dev/ttyUSB*` / `/dev/ttyACM*` (Linux).

## Config in sketch

```cpp
const unsigned long MOTOR_DURATION_MS = 1500;
const int MOTOR_SPEED = 200;  // 0-255 PWM
```

Match `MOTOR_DURATION_MS` with backend/edge `MOTOR_DURATION_MS` so the bridge cooldown aligns with physical motion.
