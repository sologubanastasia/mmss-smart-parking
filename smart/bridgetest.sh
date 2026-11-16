#!/usr/bin/env bash
# Додатково: міст Mosquitto замість шлюзу під час розриву ланки на 60 с.
# Той самий експеримент, що для gateway.py (крок 6): λ = 300 повідомлень/с.
# Запуск з кореня репозиторію: bash smart/bridgetest.sh
set -e
FILES="-f smart/docker-compose.yml -f smart/docker-compose.bridge.yml"
OUT=results/bridge.txt
: > $OUT
# Спершу зупинити все розгортання, зокрема gateway: у файлі-перевизначенні він має
# неактивний профіль, і `down` із цим файлом його не зупиняє — тоді телеметрію
# пересилали б два шляхи одночасно (міст і шлюз).
docker compose -f smart/docker-compose.yml down -v --remove-orphans
for CONF in bridge.conf bridge-qos1.conf; do
  export BRIDGE_CONF=$CONF
  docker compose $FILES down -v --remove-orphans
  if docker ps --format '{{.Names}}' | grep -q '^mmss-gateway-1$'; then
    echo "gateway працює — порівняння було б некоректним" >&2; exit 1
  fi
  docker compose $FILES up -d --build edge-broker cloud-broker collector
  sleep 3
  HZ=100 docker compose $FILES up -d sensors
  sleep 10
  echo "$(date -u +%T) розрив" | tee -a $OUT
  docker network disconnect mmss_cloud mmss-edge-broker-1
  sleep 30
  docker stats --no-stream --format 'пам’ять брокера периферії на 30-й с розриву: {{.MemUsage}}' \
    mmss-edge-broker-1 | tee -a $OUT
  sleep 30
  echo "$(date -u +%T) відновлення" | tee -a $OUT
  docker network connect mmss_cloud mmss-edge-broker-1
  sleep 60
  docker compose $FILES stop sensors
  sleep 3
  echo "== $CONF" | tee -a $OUT
  docker compose $FILES exec -T collector python stats.py | tee -a $OUT
  docker compose $FILES logs edge-broker | grep -iE "bridge|connect|drop" | tail -5 | tee -a $OUT
done
docker compose $FILES down -v
docker compose -f smart/docker-compose.yml down -v --remove-orphans
