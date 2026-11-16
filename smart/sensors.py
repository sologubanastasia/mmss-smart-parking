"""Емулятор сенсорів: публікує телеметрію MQTT за схемою повідомлення.

Емулює фрагмент Sensor Controllers зони A розумної парковки: три ультразвукові
датчики Ultrasonic Sensors над паркомісцями A-017, A-018, A-019 (потік D-05
реєстру даних ЛР1 — періодичні відліки відстані, публікація 1 Гц).

Запуск з кореня репозиторію: python smart/sensors.py
Параметри — змінні середовища: BROKER, HZ, DURATION, DROP, DUP, LATE, BAD.
"""

import json
import math
import os
import random
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

BROKER = os.environ.get("BROKER", "localhost")
HZ = float(os.environ.get("HZ", "1"))  # частота одного сенсора, 1/с (D-05: 1 Гц)
DURATION = float(os.environ.get("DURATION", "0"))  # с; 0 — без обмеження
# Частки внесених збоїв — щоб перевірити підписника
DROP = float(os.environ.get("DROP", "0"))  # пропущений показ
DUP = float(os.environ.get("DUP", "0"))  # дублікат
LATE = float(os.environ.get("LATE", "0"))  # позачерговий показ
BAD = float(os.environ.get("BAD", "0"))  # зайве зіпсоване повідомлення
BOOT_FILE = Path(os.environ.get("BOOT_FILE", "data/boot.txt"))

SITE, ZONE = "p1", "za"  # парковка і зона — рівні теми (як корпус і приміщення)
# FR-09: пристрій без heartbeat 30 с вважається недоступним. Брокер публікує
# заповіт через 1,5 · keepalive без пакетів від клієнта: 1,5 · 20 = 30 с.
KEEPALIVE = 20

# Датчик над місцем на висоті H = 2500 мм (клас MaxBotix HRXL-MaxSonar-WR,
# діапазон 300–5000 мм, роздільність 1 мм). Порожнє місце — відлік ≈ H (до
# покриття), зайняте — ≈ 1000 мм (до даху авто висотою ≈ 1,5 м).
FLOOR_MM, ROOF_MM = 2500, 1000


def spot(period, phase):
    """Модель відліку: місце зайняте, коли sin(t / period + phase) > 0.

    period задає середню тривалість стоянки (половина періоду синуса:
    π · period с), phase — зсув, щоб місця змінювали стан не одночасно.
    """
    return lambda t: ROOF_MM if math.sin(t / period + phase) > 0 else FLOOR_MM


# Сенсори предметної області: назва, величина, одиниця, шум (σ, мм),
# модель значення — функція часу t, с
SENSORS = [
    ("us-017", "dist", "mm", 6, spot(400, 0.0)),  # стоянка ≈ 21 хв
    ("us-018", "dist", "mm", 6, spot(700, 2.0)),  # ≈ 37 хв
    ("us-019", "dist", "mm", 6, spot(250, 4.0)),  # ≈ 13 хв
]


def next_boot():
    """Номер запуску: зростає після кожного перезапуску емулятора."""
    boot = int(BOOT_FILE.read_text()) + 1 if BOOT_FILE.exists() else 1
    BOOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    BOOT_FILE.write_text(str(boot))
    return boot


def connect(name):
    """Окремий клієнт MQTT для кожного сенсора — зі своїм заповітом."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                         client_id=f"{ZONE}-{name}")
    state = f"{SITE}/{ZONE}/{name}/state"
    client.will_set(state, "offline", qos=1, retain=True)
    client.connect_async(BROKER, 1883, keepalive=KEEPALIVE)
    client.loop_start()  # підключається й перепідключається сам
    while not client.is_connected():
        time.sleep(0.1)
    client.publish(state, "online", qos=1, retain=True)
    return client


def main():
    boot = next_boot()
    print(f"Підключення до {BROKER}...", flush=True)
    clients = [connect(s[0]) for s in SENSORS]
    seq = [0] * len(SENSORS)
    stats = dict(published=0, drop=0, dup=0, late=0, bad=0)
    held = None  # показ, відкладений для зміни порядку
    period = 1 / (HZ * len(SENSORS))
    start = next_t = time.monotonic()
    print(f"boot={boot}, HZ={HZ}, сенсорів: {len(SENSORS)}", flush=True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    i = 0
    try:
        while not DURATION or time.monotonic() - start < DURATION:
            k = i % len(SENSORS)
            name, qty, unit, noise, model = SENSORS[k]
            msg = {
                "dev": f"{ZONE}-{name}", "boot": boot, "seq": seq[k],
                "ts": datetime.now(timezone.utc).isoformat(
                    timespec="milliseconds").replace("+00:00", "Z"),
                "qty": qty,
                "val": round(model(time.time()) + random.gauss(0, noise)),
                "unit": unit,
            }
            seq[k] += 1
            topic = f"{SITE}/{ZONE}/{name}/tele"
            body = json.dumps(msg, separators=(",", ":"))
            faults = i >= len(SENSORS)  # перший показ кожного — без збоїв
            r = random.random()
            if faults and r < DROP:  # показ «загубився»
                stats["drop"] += 1
            elif faults and r < DROP + LATE and held is None:
                held = (k, topic, body)  # надійде пізніше
                stats["late"] += 1
            else:
                clients[k].publish(topic, body)  # QoS 0
                stats["published"] += 1
                if faults and random.random() < DUP:  # той самий ще раз
                    clients[k].publish(topic, body)
                    stats["dup"] += 1
                if held and held[0] == k:  # відкладений — після
                    clients[k].publish(held[1], held[2])
                    stats["published"] += 1
                    held = None
            if faults and random.random() < BAD:  # зіпсований формат
                clients[k].publish(topic, body[: len(body) // 2])
                stats["bad"] += 1
            i += 1
            next_t += period
            time.sleep(max(0.0, next_t - time.monotonic()))
    except KeyboardInterrupt:
        pass
    finally:
        if held:  # не лишати відкладений
            clients[held[0]].publish(held[1], held[2])
            stats["published"] += 1
        for (name, *_), client in zip(SENSORS, clients):
            client.publish(f"{SITE}/{ZONE}/{name}/state", "offline",
                           qos=1, retain=True).wait_for_publish(2)
            client.disconnect()
        print(f"Підсумок: {stats}", flush=True)


if __name__ == "__main__":
    main()
