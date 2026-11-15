#!/usr/bin/env bash
# Драбина якостей і сегменти для адаптивного потокового передавання.
# Предметна область: віддалений перегляд камери зони парковки оператором і службою безпеки.
# Запуск з кореня репозиторію: bash stream/package.sh hls (або dash)
set -e
FORMAT=${1:-hls}
SRC=data/source.mp4
FPS=15                 # частота кадрів основного потоку камери зони (D-01 ЛР1)
SEG=2                  # тривалість сегмента, с
GOP=$((SEG * FPS))     # ключовий кадр на початку кожного сегмента

# Три рівні якості за результатами заняття 1 (docs/pipeline.md):
# верхній — найменший бітрейт H.264 із SSIM ≥ 0,99 (1500 кбіт/с, 1080p);
# нижчі — за сталою кількістю біт на піксель 0,048 біт/піксель.
LADDER=(
  -map "[v1]" -b:v:0 1500k -maxrate:v:0 1650k -bufsize:v:0 3000k
  -map "[v2]" -b:v:1 670k  -maxrate:v:1 740k  -bufsize:v:1 1340k
  -map "[v3]" -b:v:2 170k  -maxrate:v:2 190k  -bufsize:v:2 340k
)
SCALE="[0:v]fps=$FPS,split=3[a][b][c];[a]scale=-2:1080[v1];"
SCALE+="[b]scale=-2:720[v2];[c]scale=-2:360[v3]"
CODEC=(-c:v libx264 -preset veryfast -pix_fmt yuv420p
       -g $GOP -keyint_min $GOP -sc_threshold 0 -an)

cd "$(dirname "$0")/.."
rm -rf "stream/$FORMAT" && mkdir -p "stream/$FORMAT"
if [ "$FORMAT" = hls ]; then
  ffmpeg -y -hide_banner -loglevel error -i $SRC -filter_complex "$SCALE" \
    "${LADDER[@]}" "${CODEC[@]}" \
    -f hls -hls_time $SEG -hls_playlist_type vod \
    -hls_segment_filename "stream/hls/v%v/seg_%03d.ts" \
    -master_pl_name master.m3u8 -var_stream_map "v:0 v:1 v:2" \
    "stream/hls/v%v/index.m3u8"
else
  ffmpeg -y -hide_banner -loglevel error -i $SRC -filter_complex "$SCALE" \
    "${LADDER[@]}" "${CODEC[@]}" \
    -f dash -seg_duration $SEG -use_template 1 -use_timeline 0 \
    -adaptation_sets "id=0,streams=v" "stream/dash/manifest.mpd"
fi
echo "Готово: stream/$FORMAT"
