"""Конвеєр «декодування — перетворення — кодування» і вимірювання якості.

Предметна область: розумна парковка, камера зони (D-01 у docs/requirements.md).
Запуск з кореня репозиторію: python pipeline/pipeline.py
Вхід: data/source.mp4
Вихід: data/reference.mkv, data/out/*.mp4, results/encoding.csv
"""
import csv
import os
import re
import subprocess
import time
from pathlib import Path

import cv2

SRC = Path("data/source.mp4")
REF = Path("data/reference.mkv")  # еталон: перетворені кадри без втрат
OUT = Path("data/out")
CSV_FILE = Path("results/encoding.csv")

# Параметри перетворення: основний потік камери зони за D-01 і припущенням A-02 ЛР1
WIDTH, HEIGHT, FPS = 1920, 1080, 15
SECONDS = 20  # тривалість фрагмента для порівняння, с
DEPTH = 24  # біт на піксель нестисненого кадру (BGR на межі OpenCV → FFmpeg)
CAMERA_ID = "CAM-01"

os.environ.setdefault("SVT_LOG", "1")  # без службових повідомлень SVT-AV1

# Алгоритмічні варіанти: назва, кодек, цільовий бітрейт.
# 3000 кбіт/с — припущення D-01 ЛР1 для H.264 1080p15; 1500 кбіт/с — удвічі менше.
VARIANTS = [
    ("h264_1500k", "h264", "1500k"),
    ("h264_3000k", "h264", "3000k"),
    ("av1_1500k", "av1", "1500k"),
    ("av1_3000k", "av1", "3000k"),
]

# Межі контрольованих паркомісць і приватна зона в нормованих координатах
# (x0, y0, x1, y1) — не залежать від роздільної здатності кадру.
SPOTS = {
    "P01": (0.320, 0.838, 0.445, 0.995),
    "P02": (0.448, 0.847, 0.578, 1.000),
    "P03": (0.557, 0.759, 0.698, 0.981),
    "P04": (0.357, 0.634, 0.432, 0.736),
    "P05": (0.271, 0.634, 0.333, 0.736),
    "P06": (0.193, 0.653, 0.255, 0.750),
}
PRIVATE_ZONE = (0.000, 0.185, 0.229, 0.255)  # вікна сусіднього готелю
MOSAIC = 16  # розмір блока пікселізації, пікселів

stats = {"decode_s": 0.0, "transform_s": 0.0}


def to_pixels(box, width, height):
    x0, y0, x1, y1 = box
    return int(x0 * width), int(y0 * height), int(x1 * width), int(y1 * height)


def process(frame, t):
    """Перетворення одного кадру. У ЛР 4 сюди підключається модель ONNX.

    1. Маскування приватної зони (C-03, NFR-05 ЛР1) — пікселізація.
    2. Накладання меж паркомісць, які аналізує Video Analytics.
    3. Мітка часу та ідентифікатор камери (вбудовані шрифти OpenCV — лише латиниця).
    """
    h, w = frame.shape[:2]
    x0, y0, x1, y1 = to_pixels(PRIVATE_ZONE, w, h)
    zone = frame[y0:y1, x0:x1]
    small = cv2.resize(zone, (max(1, (x1 - x0) // MOSAIC), max(1, (y1 - y0) // MOSAIC)),
                       interpolation=cv2.INTER_LINEAR)
    frame[y0:y1, x0:x1] = cv2.resize(small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)

    scale = h / 1080
    for name, box in SPOTS.items():
        sx0, sy0, sx1, sy1 = to_pixels(box, w, h)
        cv2.rectangle(frame, (sx0, sy0), (sx1, sy1), (0, 220, 255), max(1, round(2 * scale)))
        cv2.putText(frame, name, (sx0 + 6, sy0 + round(26 * scale)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8 * scale, (0, 220, 255), max(1, round(2 * scale)), cv2.LINE_AA)

    label = f"{CAMERA_ID}  t={t:6.2f} s"
    font_scale, thickness = 1.2 * scale, max(1, round(2 * scale))
    (tw, th), base = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
    origin = (20, round(50 * scale))
    cv2.rectangle(frame, (origin[0] - 8, origin[1] - th - 8), (origin[0] + tw + 8, origin[1] + base + 6),
                  (0, 0, 0), cv2.FILLED)  # темна підкладка: мітка читається на світлому небі
    cv2.putText(frame, label, origin, cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255),
                thickness, cv2.LINE_AA)
    return frame


def transform():
    """Декодування (OpenCV) → перетворення → еталон без втрат (FFmpeg)."""
    cap = cv2.VideoCapture(str(SRC))
    if not cap.isOpened():
        raise SystemExit(f"Не вдалося відкрити {SRC}")
    src_fps = cap.get(cv2.CAP_PROP_FPS)
    if src_fps < FPS:
        raise SystemExit(f"FPS = {FPS} більша за частоту джерела {src_fps}")
    step = src_fps / FPS  # скільки вхідних кадрів на один вихідний
    writer = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "bgr24",
         "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-qp", "0", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", str(REF)],
        stdin=subprocess.PIPE)
    index, frames, next_index = 0, 0, 0.0
    while frames < SECONDS * FPS:
        started = time.perf_counter()
        ok, frame = cap.read()  # декодування
        stats["decode_s"] += time.perf_counter() - started
        if not ok:
            break
        index += 1
        if index - 1 < next_index:  # зменшення частоти кадрів
            continue
        next_index += step
        started = time.perf_counter()
        frame = cv2.resize(frame, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
        frame = process(frame, frames / FPS)
        stats["transform_s"] += time.perf_counter() - started
        writer.stdin.write(frame.tobytes())
        frames += 1
    cap.release()
    writer.stdin.close()
    writer.wait()
    return frames


def av1_encoder():
    """Обирає наявний кодер AV1: SVT-AV1, а якщо його немає — libaom."""
    names = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                           capture_output=True, text=True).stdout
    if "libsvtav1" in names:
        return ["-c:v", "libsvtav1", "-preset", "8"]
    if "libaom-av1" in names:
        return ["-c:v", "libaom-av1", "-cpu-used", "6", "-row-mt", "1"]
    raise SystemExit("У збірці FFmpeg немає кодера AV1")


def encode(codec, bitrate, out):
    """Кодування еталона одним варіантом; повертає час кодування, с."""
    args = (["-c:v", "libx264", "-preset", "medium"] if codec == "h264"
            else av1_encoder())
    start = time.perf_counter()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(REF),
                    *args, "-b:v", bitrate, "-an", str(out)], check=True)
    return time.perf_counter() - start


def quality(out):
    """PSNR (дБ) і SSIM закодованого файлу відносно еталона засобами FFmpeg."""
    result = {}
    for name, pattern in (("psnr", r"average:(\S+)"), ("ssim", r"All:(\S+)")):
        cmd = ["ffmpeg", "-hide_banner", "-i", str(out), "-i", str(REF),
               "-lavfi", name, "-f", "null", "-"]
        log = subprocess.run(cmd, capture_output=True, text=True).stderr
        result[name] = float(re.findall(pattern, log)[-1])
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    frames = transform()
    duration = frames / FPS
    raw_kbps = WIDTH * HEIGHT * FPS * DEPTH / 1000
    print(f"Еталон: {frames} кадрів, {duration:.1f} с, {WIDTH}x{HEIGHT}, {FPS} кадр/с")
    print(f"Декодування: {stats['decode_s'] / frames * 1000:.1f} мс на вихідний кадр; "
          f"перетворення: {stats['transform_s'] / frames * 1000:.1f} мс на кадр; "
          f"бюджет 1/f = {1000 / FPS:.1f} мс")

    rows = []
    for name, codec, bitrate in VARIANTS:
        out = OUT / f"{name}.mp4"
        seconds = encode(codec, bitrate, out)
        size = out.stat().st_size
        kbps = size * 8 / duration / 1000
        q = quality(out)
        rows.append({
            "variant": name, "codec": codec,
            "target_kbps": int(bitrate[:-1]), "size_kb": round(size / 1024),
            "actual_kbps": round(kbps), "compression": round(raw_kbps / kbps),
            "encode_s": round(seconds, 1), "psnr_db": round(q["psnr"], 2),
            "ssim": round(q["ssim"], 4)})
        print(rows[-1], f"швидкість {duration / seconds:.1f}× реального часу")
    with CSV_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Результати: {CSV_FILE}")


if __name__ == "__main__":
    main()
