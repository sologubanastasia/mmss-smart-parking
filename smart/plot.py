"""Графік залежності затримки й втрат від навантаження.

Запуск з кореня репозиторію: python smart/plot.py
Вхід: results/load.csv; вихід: results/latency.png
"""

import csv
import os

import matplotlib

matplotlib.use("Agg")  # без вікна — одразу у файл
import matplotlib.pyplot as plt  # noqa: E402

# Пропускна здатність Θ, повідомлень/с, визначена за журналом шлюзу
# (docs/deployment.md, «Навантаження»); 0 — не позначати на графіку
THETA = float(os.environ.get("THETA", "0"))

with open("results/load.csv", encoding="utf-8") as f:
    rows = sorted(csv.DictReader(f), key=lambda r: float(r["rate"]))
rate = [float(r["rate"]) for r in rows]

fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(rate, [float(r["lat_mean_ms"]) for r in rows], "o-",
        label="середня затримка")
ax.plot(rate, [float(r["lat_p95_ms"]) for r in rows], "s--",
        label="95-й процентиль")
ax.set_xlabel("Навантаження λ, повідомлень/с")
ax.set_ylabel("Затримка доставки, мс")
ax.set_yscale("log")
ax.grid(True, which="both", alpha=0.3)
if THETA:
    ax.axvline(THETA, color="gray", linestyle="-.", linewidth=1)
    ax.annotate(f"Θ ≈ {THETA:.0f}", (THETA, 0.97), xycoords=("data", "axes fraction"),
                xytext=(4, -4), textcoords="offset points", va="top", color="gray")

loss = ax.twinx()  # друга вісь — частка втрат
loss.plot(rate, [100 * float(r["loss"]) for r in rows], "^:",
          color="tab:red", label="втрати ε")
loss.set_ylabel("Частка втрат ε, %")
loss.set_ylim(bottom=0)

lines = ax.get_lines()[:2] + loss.get_lines()
ax.legend(lines, [x.get_label() for x in lines], loc="upper left")
ax.set_title("Залежність затримки й втрат від навантаження (шлюз зони A)")
fig.tight_layout()
fig.savefig("results/latency.png", dpi=150)
print("Графік: results/latency.png")
