# Розумна парковка з визначенням вільних місць

Комплексна робота з дисципліни **«Архітектури мультимедійних та смартсистем»**:

| Лабораторна | Тема | Результати |
|---|---|---|
| ЛР1 | Аналіз предметної області та архітектурний опис за ISO/IEC/IEEE 42010:2022 | [requirements.md](docs/requirements.md), [діаграми](#діаграми), ADR-0001–0003, [сценарії якості](docs/quality-scenarios.md) |
| ЛР2 | Конвеєр оброблення та адаптивне потокове передавання | [pipeline.md](docs/pipeline.md), [qoe.md](docs/qoe.md), [ADR-0004](docs/adr/0004-stream-ladder.md), [розділ нижче](#лр2-конвеєр-і-потокове-передавання) |
| ЛР3 | Архітектура смартсистеми: сенсорні дані, розподілене розгортання та шаблони | [telemetry.md](docs/telemetry.md), [deployment.md](docs/deployment.md), [ADR-0005](docs/adr/0005-telemetry-patterns.md), [ADR-0006](docs/adr/0006-gateway-language-stack.md), [розділ нижче](#лр3-сенсорні-дані-та-розгортання-edgecloud) |

Система визначає зайнятість 500 паркомісць за відео й ультразвуковими датчиками, розпізнає номери на в'їзді та виїзді, керує шлагбаумом і табло та показує водіям вільні місця. Ця предметна область зберігається в лабораторних роботах 1–4.

## Модальності та сенсорні канали

- відео 50 камер зон (основний потік 1080p, 15 кадр/с — для запису; допоміжний 360p, 5 кадр/с — для аналітики);
- відео й кадри номерних знаків з 2 камер в'їзду/виїзду;
- числова телеметрія 500 ультразвукових датчиків (опитування 10 Гц);
- текстові результати розпізнавання номерів;
- дискретні події та команди шлагбаума, журнали й метрики.

## Архітектурна ідея

Контур «сприйняття — рішення — дія» замикається на edge-вузлі парковки. Відеоаналітика, об'єднання двох каналів, рішення про доступ, керування шлагбаумом і табло працюють без центрального сервера. Сервер надає API для водіїв і персоналу, довготривале зберігання, політики доступу, звітність і спостережуваність. Відео, телеметрія й команди мають окремі канали, а наскрізна затримка має явний бюджет із власником кожної частки.

## Документація

| Документ | Зміст |
|---|---|
| [docs/requirements.md](docs/requirements.md) | Призначення, межа, класифікація, сторони, реєстр даних і розрахунки, 10 FR, 6 NFR, бюджет затримки, подання та правила відповідності, матриця трасовності, принципи побудови |
| [docs/adr/0001-edge-processing.md](docs/adr/0001-edge-processing.md) | ADR-0001: розміщення обчислень і рішення про доступ на edge-вузлі |
| [docs/adr/0002-data-transport.md](docs/adr/0002-data-transport.md) | ADR-0002: окремі транспорти відео, телеметрії та команд |
| [docs/adr/0003-event-storage.md](docs/adr/0003-event-storage.md) | ADR-0003: подійне зберігання й розділення сховищ |
| [docs/quality-scenarios.md](docs/quality-scenarios.md) | Дерево корисності, QS-01 (швидкодія), QS-02 (доступність), результати спрощеного ATAM |
| [docs/defense-notes.md](docs/defense-notes.md) | Відповіді на контрольні запитання |

## ЛР2: конвеєр і потокове передавання

Потрібні FFmpeg 6+ (з `libx264` і `libsvtav1` або `libaom-av1`), Python 3.10+ і Node.js 18+ (лише для автоматизованого прогону QoE). Медіафайли (`data/`) і сегменти потоку в репозиторій не входять — їх відтворюють командами нижче.

```bash
python -m venv .venv && source .venv/Scripts/activate     # Linux, macOS: .venv/bin/activate
pip install -r pipeline/requirements.txt
python pipeline/pipeline.py      # еталон, 4 варіанти кодування → results/encoding.csv
python pipeline/sweep.py         # додатково: 8 точок і BD-rate → results/encoding_sweep.csv
bash stream/package.sh hls       # драбина 1080p/720p/360p → stream/hls/
bash stream/package.sh dash      # те саме для MPEG-DASH → stream/dash/
cd stream && python -m http.server 8000                    # http://localhost:8000/player.html
```

Показники QoE знімаються вручну в DevTools (Network → Throttling, профілі П1–П3) або тим самим механізмом автоматично: `cd tools/qoe && npm install && node measure_qoe.mjs` (сервер має працювати) → `results/qoe.csv`, `results/qoe_extra.csv`.

| Файл | Зміст |
|---|---|
| [pipeline/pipeline.py](pipeline/pipeline.py) | Декодування (OpenCV) → перетворення й `process()` → еталон без втрат → H.264/AV1 → PSNR, SSIM |
| [pipeline/sweep.py](pipeline/sweep.py) | Криві «бітрейт — якість» і BD-rate AV1 відносно H.264 |
| [stream/package.sh](stream/package.sh), [stream/player.html](stream/player.html) | Драбина якостей і сегменти HLS/DASH; плеєр hls.js/dash.js з обліком QoE |
| [results/](results) | `encoding.csv`, `encoding_sweep.csv`, `qoe.csv`, `qoe_extra.csv` |
| [docs/pipeline.md](docs/pipeline.md), [docs/qoe.md](docs/qoe.md) | Звіти занять 1 і 2 |
| [docs/adr/0004-stream-ladder.md](docs/adr/0004-stream-ladder.md) | Рішення щодо кодека, драбини, сегмента й початкового рівня |

## ЛР3: сенсорні дані та розгортання edge–cloud

Потрібні Docker Desktop (або Docker Engine з `docker compose` v2) і Python 3.10+ з `paho-mqtt==2.1.0` і `matplotlib`. Бази SQLite лежать у `data/` і томах Docker, у репозиторій не входять. У Windows команди виконуються в Git Bash.

```bash
source .venv/Scripts/activate && pip install paho-mqtt==2.1.0 matplotlib   # Linux, macOS: .venv/bin/activate
export COMPOSE_FILE=smart/docker-compose.yml

# Заняття 1: лише брокер з портом 127.0.0.1:1883 (роль брокера заняття 1), складники — на хості
docker compose up -d cloud-broker
python smart/collector.py                                                   # термінал 2
DROP=0.03 DUP=0.02 LATE=0.03 BAD=0.02 HZ=20 DURATION=30 python smart/sensors.py
python smart/stats.py

# Заняття 2: периферійний і серверний складники (підписника на хості спершу зупинити)
docker compose down && docker compose up -d --build
docker compose exec -T collector python stats.py
bash smart/loadtest.sh && THETA=550 python smart/plot.py                   # 9 ступенів → results/load.csv, latency.png
bash smart/bottleneck.sh                                                    # додатково: смуга чи процесор → results/bottleneck.csv
bash smart/bridgetest.sh                                                    # додатково: міст Mosquitto під час розриву → results/bridge.txt
```

| Файл | Зміст |
|---|---|
| [smart/sensors.py](smart/sensors.py) | Емулятор трьох ультразвукових датчиків зони A (D-05), внесення збоїв `DROP`, `DUP`, `LATE`, `BAD` |
| [smart/collector.py](smart/collector.py), [smart/stats.py](smart/stats.py) | Sensor Ingest: перевірка схеми, `readings`/`anomalies`/`rejected`; підсумок λ, ε, Lд |
| [smart/gateway.py](smart/gateway.py) | Sync Agent + Local Event Buffer: буфер SQLite, QoS 1, видалення після PUBACK |
| [smart/docker-compose.yml](smart/docker-compose.yml), [smart/Dockerfile](smart/Dockerfile), [smart/broker/mosquitto.conf](smart/broker/mosquitto.conf) | Мережі `edge` і `cloud`, ліміти периферії, томи |
| [smart/loadtest.sh](smart/loadtest.sh), [smart/plot.py](smart/plot.py) | Навантажувальне випробування і графік |
| [smart/bottleneck.sh](smart/bottleneck.sh), [smart/bridgetest.sh](smart/bridgetest.sh), [smart/docker-compose.bridge.yml](smart/docker-compose.bridge.yml) | Додаткові експерименти: вузьке місце шлюзу, міст Mosquitto |
| [docs/telemetry.md](docs/telemetry.md), [docs/deployment.md](docs/deployment.md) | Звіти занять 1 і 2 |
| [docs/adr/0005-telemetry-patterns.md](docs/adr/0005-telemetry-patterns.md), [docs/adr/0006-gateway-language-stack.md](docs/adr/0006-gateway-language-stack.md) | Рішення щодо шаблонів і щодо мови та стека шлюзу |

## Діаграми

| Подання | Точка зору | Джерело | Зображення |
|---|---|---|---|
| Контекстне | Межа системи (рівень 1 C4) | [context.mmd](docs/diagrams/context.mmd) | [context.svg](docs/diagrams/context.svg) |
| Компонентне | Функційна декомпозиція | [components.mmd](docs/diagrams/components.mmd) | [components.svg](docs/diagrams/components.svg) |
| Розгортання | Вузли, мережі, відмови | [deployment.mmd](docs/diagrams/deployment.mmd) | [deployment.svg](docs/diagrams/deployment.svg) |

Як переглянути:
- SVG відкриваються в браузері або прямо на GitHub;
- `.mmd` — у VS Code з розширенням Markdown Mermaid (`bierner.markdown-mermaid`) або на [mermaid.live](https://mermaid.live/).

Діаграми використовують розкладку ELK (`layout: elk`), яку підтримують mermaid-cli 11 і mermaid.live.

## Генерація SVG

Єдиним джерелом діаграм є файли `.mmd`; SVG генеруються з них і вручну не редагуються. Потрібен Node.js 18+:

```bash
cd docs/diagrams
for f in context components deployment; do
  npx -y @mermaid-js/mermaid-cli@11.4.2 -b white -i $f.mmd -o $f.svg
done
```

Якщо `mermaid-cli` не може завантажити Chromium, передайте шлях до встановленого браузера через файл налаштувань Puppeteer (`-p puppeteer.json` з полем `executablePath`) або збережіть SVG на mermaid.live під тими самими назвами.

## Перевірка узгодженості

```bash
python tools/validate_project.py
```

Скрипт перевіряє:
- комплектність файлів, кількість FR і NFR та їхні критерії;
- шкалу критичності в реєстрі даних і суму бюджету затримки з власниками часток;
- присутність кожної канонічної назви в `.mmd` і згенерованих `.svg` (правила відповідності R1–R5);
- згадування кожної NFR в ADR, повноту сценаріїв якості та кількість комітів.

## Склад репозиторію

```text
mmss-lab/
├── README.md
├── docs/
│   ├── requirements.md
│   ├── quality-scenarios.md
│   ├── defense-notes.md
│   ├── adr/
│   │   ├── 0001-edge-processing.md
│   │   ├── 0002-data-transport.md
│   │   └── 0003-event-storage.md
│   ├── pipeline.md                  # ЛР2, заняття 1
│   ├── qoe.md                       # ЛР2, заняття 2
│   ├── adr/0004-stream-ladder.md    # ЛР2
│   ├── telemetry.md                 # ЛР3, заняття 1
│   ├── deployment.md                # ЛР3, заняття 2
│   ├── adr/0005-telemetry-patterns.md, adr/0006-gateway-language-stack.md   # ЛР3
│   └── diagrams/
│       ├── context.mmd      context.svg
│       ├── components.mmd   components.svg
│       └── deployment.mmd   deployment.svg
├── pipeline/                        # ЛР2: pipeline.py, sweep.py, requirements.txt
├── stream/                          # ЛР2: package.sh, player.html, vendor/, маніфести hls/ і dash/
├── smart/                           # ЛР3: sensors.py, collector.py, stats.py, gateway.py, Dockerfile,
│                                    #      docker-compose.yml, broker/, loadtest.sh, plot.py, додаткові сценарії
├── results/                         # ЛР2: encoding*.csv, qoe*.csv; ЛР3: load.csv, latency.png, bottleneck.csv, bridge.txt
└── tools/
    ├── validate_project.py
    └── qoe/                         # ЛР2: автоматизований прогін QoE (Puppeteer)
```

## Історія версій опису

Архітектурний опис ведеться як елемент конфігурації: кожна базова версія позначена тегом.

| Версія | Дата | Тег | Зміни |
|---|---|---|---|
| 1.0 | 2026-10-10 | `lab1-v1.0` | Версія, подана в Google Classroom |
| 1.1 | 2026-11-15 | `lab1-v1.1` | Самоперевірка за лекціями 1–4 (див. нижче) |

Що змінилося у версії 1.1:
- **Рішення про доступ.** Перевірка сценарієм QS-02 показала, що без сервера автоматичний в'їзд неможливий, тому рішення про доступ перенесено на edge-вузол (Edge Access Control, ADR-0001 ред. 2).
- **Синхронізація каналів.** NFR-04 узгоджено з частотою датчиків: опитування 10 Гц, публікація подій за зміною, бюджет розходження міток.
- **Бюджет затримки.** Отримав власників часток і запас 650 мс.
- **Діаграми.** SVG тепер генеруються mermaid-cli з `.mmd`, а резервний рендерер вилучено. Подання узгоджено між собою за правилами R1–R5.
- **Числа в ADR.** Додано пропускну здатність WAN, оцінку навантаження edge-вузла, таблиці критеріїв і окремий Control Broker.
- **Вимоги.** До реєстру даних додано правовий режим і службові витрати телеметрії; до вимог — пріоритезацію, NFR безпеки, принципи побудови й покриття трасовності.
