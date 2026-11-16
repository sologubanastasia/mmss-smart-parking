#!/usr/bin/env bash
# Додатково: пошук вузького місця шлюзу. Ступінь λ = 900 повідомлень/с
# повторюється в трьох конфігураціях і показує, що саме обмежує Θ:
#   A — як у loadtest.sh: смуга 1000 кбіт/с, 0,25 CPU;
#   B — без обмеження смуги (UPLINK_KBPS=0), 0,25 CPU;
#   C — смуга 1000 кбіт/с, 1 CPU (docker update).
# D, E — проміжні ступені 450 і 540 повідомлень/с у конфігурації A, щоб уточнити Θ.
# Запуск з кореня репозиторію після loadtest.sh: bash smart/bottleneck.sh
set -e
export COMPOSE_FILE=smart/docker-compose.yml MAX_ROWS=10000
OUT=results/bottleneck.csv
run() { # $1 — назва конфігурації, $2 — UPLINK_KBPS, $3 — cpus шлюзу, $4 — HZ
  UPLINK_KBPS=$2 docker compose up -d --no-deps --force-recreate gateway
  docker update --cpus "$3" mmss-gateway-1 > /dev/null
  sleep 5
  HZ=$4 DURATION=30 docker compose up -d sensors
  sleep 35
  peak=$(docker compose logs --since 40s gateway | sed -n 's/.*буфер=\([0-9]*\).*/\1/p' | sort -n | tail -1)
  until docker compose logs --tail 1 gateway | grep -q "буфер=0 "; do sleep 2; done
  row=$(docker compose exec -T collector python stats.py --csv | tail -1)
  echo "$1,$2,$3,$4,$peak,$row" | tee -a $OUT
}
echo "config,uplink_kbps,cpus,hz,peak_backlog,boot,rate,sent,received,loss,late,dup,lat_mean_ms,lat_p95_ms,lat_max_ms" > $OUT
run A 1000 0.25 300
run B 0 0.25 300
run C 1000 1.0 300
run D 1000 0.25 150
run E 1000 0.25 180
UPLINK_KBPS=1000 docker compose up -d --no-deps --force-recreate gateway # повернути конфігурацію
