"""Додаткове дослідження: криві «бітрейт — якість» і BD-rate (Bjøntegaard).

Використовує еталон data/reference.mkv, сформований pipeline.py (запускати після нього).
Запуск з кореня репозиторію: python pipeline/sweep.py
Вихід: results/encoding_sweep.csv, BD-rate AV1 відносно H.264 у stdout.
"""
import csv
from pathlib import Path

import numpy as np

from pipeline import FPS, HEIGHT, OUT, REF, SECONDS, WIDTH, encode, quality

SWEEP_CSV = Path("results/encoding_sweep.csv")
BITRATES = [500, 1000, 1500, 3000]  # кбіт/с: чотири точки на кодек для BD-rate


def bd_rate(rate_a, psnr_a, rate_b, psnr_b):
    """Середня різниця бітрейту B відносно A за однакової якості, % (Bjøntegaard, 2001)."""
    log_a, log_b = np.log(rate_a), np.log(rate_b)
    fit_a, fit_b = np.polyfit(psnr_a, log_a, 3), np.polyfit(psnr_b, log_b, 3)
    low, high = max(min(psnr_a), min(psnr_b)), min(max(psnr_a), max(psnr_b))
    int_a, int_b = np.polyint(fit_a), np.polyint(fit_b)
    avg_a = (np.polyval(int_a, high) - np.polyval(int_a, low)) / (high - low)
    avg_b = (np.polyval(int_b, high) - np.polyval(int_b, low)) / (high - low)
    return (np.exp(avg_b - avg_a) - 1) * 100


def main():
    if not REF.exists():
        raise SystemExit(f"Немає еталона {REF}: спершу запустіть pipeline/pipeline.py")
    duration = SECONDS
    rows = []
    for codec in ("h264", "av1"):
        for kbps in BITRATES:
            out = OUT / f"sweep_{codec}_{kbps}k.mp4"
            seconds = encode(codec, f"{kbps}k", out)
            actual = out.stat().st_size * 8 / duration / 1000
            q = quality(out)
            rows.append({"codec": codec, "target_kbps": kbps, "actual_kbps": round(actual),
                         "encode_s": round(seconds, 1), "psnr_db": round(q["psnr"], 2),
                         "ssim": round(q["ssim"], 4)})
            print(rows[-1])
    SWEEP_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SWEEP_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    def series(codec, key):
        return np.array([r[key] for r in rows if r["codec"] == codec], dtype=float)

    value = bd_rate(series("h264", "actual_kbps"), series("h264", "psnr_db"),
                    series("av1", "actual_kbps"), series("av1", "psnr_db"))
    print(f"Матеріал: {WIDTH}x{HEIGHT}, {FPS} кадр/с, {SECONDS} с")
    print(f"BD-rate AV1 відносно H.264 (PSNR): {value:+.1f} %")
    print(f"Результати: {SWEEP_CSV}")


if __name__ == "__main__":
    main()
