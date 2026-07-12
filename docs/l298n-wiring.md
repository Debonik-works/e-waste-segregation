# L298N motor driver wiring

Two L-shaped DC geared motors on one conveyor — **both always rotate together**.

## Block diagram

```text
                  +------------------+
  Battery/PSU --->|      L298N       |
  (e.g. 9–12V)    |  VMOT   GND  5V  |
                  | IN1 IN2 ENA      |---- Motor A
                  | IN3 IN4 ENB      |---- Motor B
                  +--------+---------+
                           |
                    Arduino Nano
                    D2 D3 D9 / D4 D5 D10
```

## Connections

| L298N | Connects to |
|-------|-------------|
| OUT1 / OUT2 | Motor A leads |
| OUT3 / OUT4 | Motor B leads |
| IN1 | Nano D2 |
| IN2 | Nano D3 |
| IN3 | Nano D4 |
| IN4 | Nano D5 |
| ENA | Nano D9 (PWM) — remove jumper if present |
| ENB | Nano D10 (PWM) — remove jumper if present |
| GND | Nano GND **and** battery GND (common ground) |
| VCC / 5V | Nano 5V **or** onboard regulator (module-dependent) |
| VS / VMOT | Motor battery positive |

## Direction convention (firmware)

- `RIGHT` (e-waste): IN1/IN3 HIGH, IN2/IN4 LOW
- `LEFT` (reject): opposite polarity

If the conveyor moves the wrong way, swap either motor leads or invert the firmware directions.

## Safety

- Never share motor VMOT with the Nano’s USB 5V rail
- Add flyback protection (L298N modules usually include diodes)
- Start with low PWM (`MOTOR_SPEED`) and short `MOTOR_DURATION_MS`
