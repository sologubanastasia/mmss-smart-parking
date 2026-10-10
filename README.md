# Розумна парковка з визначенням вільних місць

Лабораторна робота №1 із дисципліни **«Архітектури мультимедійних та смартсистем»**. Система визначає зайнятість паркомісць за відео й ультразвуковими датчиками, реєструє автомобілі на в'їзді та виїзді, керує шлагбаумом і показує водіям доступні місця.

## Модальності та сенсорні канали

- відео з камер зон парковки;
- зображення номерних знаків;
- числова телеметрія ультразвукових датчиків;
- дискретні події шлагбаума;
- текстові результати OCR;
- керувальні команди, журнали та метрики.

## Архітектурна ідея

Критичне оброблення виконується на edge-вузлі парковки. Відеоаналітика та сенсорні дані об'єднуються локально, тому визначення зайнятості й базове керування продовжуються навіть без центрального сервера. Сервер відповідає за API, довготривале зберігання, клієнтські інтерфейси, статистику й адміністрування.

## Документація

- [Вимоги та трасовність](docs/requirements.md)
- [Сценарії атрибутів якості](docs/quality-scenarios.md)
- [ADR-0001: edge-оброблення](docs/adr/0001-edge-processing.md)
- [ADR-0002: транспорт даних](docs/adr/0002-data-transport.md)
- [ADR-0003: подійне зберігання](docs/adr/0003-event-storage.md)
- [Підготовка до захисту](docs/defense-notes.md)

## Діаграми

| Подання | Mermaid | SVG |
|---|---|---|
| Контекстне | [context.mmd](docs/diagrams/context.mmd) | [context.svg](docs/diagrams/context.svg) |
| Компонентне | [components.mmd](docs/diagrams/components.mmd) | [components.svg](docs/diagrams/components.svg) |
| Розгортання | [deployment.mmd](docs/diagrams/deployment.mmd) | [deployment.svg](docs/diagrams/deployment.svg) |

Щоб переглянути `.mmd`, відкрийте файл у VS Code з розширенням Markdown Mermaid або вставте його в [Mermaid Live Editor](https://mermaid.live/). SVG відкриваються у звичайному браузері.

## Генерація SVG

За наявності Node.js 18+ та `mermaid-cli`:

```bash
cd docs/diagrams
npx -y @mermaid-js/mermaid-cli -i context.mmd -o context.svg
npx -y @mermaid-js/mermaid-cli -i components.mmd -o components.svg
npx -y @mermaid-js/mermaid-cli -i deployment.mmd -o deployment.svg
```

Якщо Mermaid CLI недоступний, у репозиторії є локальний резервний рендерер без зовнішніх залежностей:

```bash
python tools/render_fallback_svgs.py
```

Авторитетними вихідними файлами діаграм залишаються `.mmd`; резервний рендерер зберігає канонічні назви вузлів і ті самі архітектурні потоки, використовуючи детерміноване ортогональне трасування стрілок.

## Склад репозиторію

```text
mmss-lab/
├── README.md
└── docs/
    ├── requirements.md
    ├── quality-scenarios.md
    ├── defense-notes.md
    ├── adr/
    │   ├── 0001-edge-processing.md
    │   ├── 0002-data-transport.md
    │   └── 0003-event-storage.md
    └── diagrams/
        ├── context.mmd / context.svg
        ├── components.mmd / components.svg
        └── deployment.mmd / deployment.svg
```
