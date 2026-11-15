"""Перевірка комплектності та узгодженості репозиторію ЛР1 без зовнішніх залежностей.

Запуск: python tools/validate_project.py [--skip-git]
"""

from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DIAGRAMS = DOCS / "diagrams"
VIEWS = ("context", "components", "deployment")
errors: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Текст від заголовка до наступного заголовка будь-якого рівня."""
    start = text.find(heading)
    if start < 0:
        return ""
    rest = text[start + len(heading):]
    match = re.search(r"^#+ ", rest, re.MULTILINE)
    return rest[: match.start()] if match else rest


def table_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if line.startswith("|") and not re.match(r"^\|[\s:|-]+\|$", line):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows[1:]  # без рядка заголовків


def validate_required_files() -> None:
    required = [
        "README.md",
        "docs/requirements.md",
        "docs/quality-scenarios.md",
        *(f"docs/diagrams/{view}.{ext}" for view in VIEWS for ext in ("mmd", "svg")),
    ]
    for name in required:
        check((ROOT / name).is_file(), f"Немає обов'язкового файлу {name}")
    adrs = sorted((DOCS / "adr").glob("000[1-3]-*.md"))
    check(len(adrs) == 3, f"Очікується три ADR 0001–0003, знайдено {len(adrs)}")


def validate_requirements() -> None:
    text = read(DOCS / "requirements.md")
    for heading in ("## 1. Призначення", "## 3. Класифікація", "## 4. Зацікавлені сторони", "## 6. Реєстр даних"):
        check(heading in text, f"requirements.md: немає розділу «{heading}»")

    stakeholders = table_rows(section(text, "## 4. Зацікавлені сторони"))
    check(len(stakeholders) >= 4, "Потрібно щонайменше 4 зацікавлені сторони")

    register = [row for row in table_rows(section(text, "## 6. Реєстр даних")) if row and row[0].startswith("D-")]
    check(len(register) >= 5, "Реєстр даних має містити щонайменше 5 рядків")
    for row in register:
        check(row[7] in {"Висока", "Середня", "Низька"}, f"{row[0]}: критичність поза шкалою висока/середня/низька")
    check("R = w × h × f × d" in text, "Немає розрахунку обсягу відеопотоку R = w × h × f × d")

    functional = re.findall(r"^### (FR-\d{2})\.", text, re.MULTILINE)
    check(8 <= len(functional) <= 10, f"Функційних вимог має бути 8–10, знайдено {len(functional)}")
    for block in re.split(r"^### FR-\d{2}\.", text, flags=re.MULTILINE)[1:]:
        check("**Критерій приймання:**" in block.split("\n## ")[0], "Кожна FR має містити критерій приймання")

    nfr_rows = [row for row in table_rows(section(text, "## 8. Нефункційні вимоги")) if row and row[0].startswith("NFR-")]
    check(5 <= len(nfr_rows) <= 6, f"Нефункційних вимог має бути 5–6, знайдено {len(nfr_rows)}")
    dimensions = {row[1] for row in nfr_rows}
    for dimension in ("Реальний час", "Масштабованість", "Розподіленість", "Мультимодальність"):
        check(dimension in dimensions, f"NFR не охоплюють вимір «{dimension}»")
    for row in nfr_rows:
        check(bool(re.search(r"\d", row[2])), f"{row[0]}: немає числового значення")
        check(len(row) >= 5 and row[4] != "", f"{row[0]}: немає засобу вимірювання")

    budget = table_rows(section(text, "### 8.1. Бюджет"))
    total = 0
    for row in budget:
        value = int(re.sub(r"\D", "", row[-1]) or 0)
        if row[0].startswith("**Разом"):
            check(value == 2000 and total == 2000, f"Сума часток бюджету {total} мс не дорівнює 2000 мс")
            continue
        total += value
        if row[0] != "Запас":
            check(row[3] not in {"", "—"}, f"Частка бюджету «{row[0]}» не має власника")

    matrix = section(text, "## 12. Матриця трасовності")
    for requirement in functional + [row[0] for row in nfr_rows]:
        check(f"| {requirement} |" in matrix, f"{requirement} відсутня в матриці трасовності")

    viewpoints = table_rows(section(text, "## 11. Архітектурні подання"))
    check(len(viewpoints) == 3, "Таблиця «подання — точка зору — сторона — інтерес» має містити три рядки")


def canonical_names() -> dict[str, list[str]]:
    rows = table_rows(section(read(DOCS / "requirements.md"), "### 11.1. Канонічні назви"))
    return {row[0]: [name.strip() for name in row[1].split(",")] for row in rows}


def validate_correspondences() -> None:
    names = canonical_names()
    mmd = {view: read(DIAGRAMS / f"{view}.mmd") for view in VIEWS}
    svg = {view: read(DIAGRAMS / f"{view}.svg") for view in VIEWS}

    for view in VIEWS:
        check('aria-roledescription="flowchart' in svg[view], f"{view}.svg не згенеровано Mermaid із {view}.mmd")

    for zone, elements in names.items():
        infrastructure = zone.startswith("Інфраструктура")
        external = zone.startswith("Зовнішні")
        for element in elements:
            targets = ["deployment"] if infrastructure else ["components", "deployment"]
            if external:
                targets.append("context")
            for view in targets:
                check(element in mmd[view], f"R1/R5: «{element}» відсутній у {view}.mmd")
                check(element in svg[view], f"R5: «{element}» відсутній у {view}.svg — перегенеруйте SVG")

    documents = [read(path) for path in (DOCS / "adr").glob("*.md")] + [read(DOCS / "quality-scenarios.md")]
    known = {element for elements in names.values() for element in elements}
    for legacy in ("MQTT Broker", "Operator Dashboard", "Navigation Service"):
        check(all(legacy not in document for document in documents), f"R5: застаріла назва «{legacy}» в ADR або сценаріях")
    check(len(known) >= 30, "Канонічна таблиця назв неповна")


def validate_adrs_and_scenarios() -> None:
    requirements = read(DOCS / "requirements.md")
    nfr_ids = set(re.findall(r"^\| (NFR-\d{2}) \|", requirements, re.MULTILINE))
    adr_text = ""
    for path in sorted((DOCS / "adr").glob("*.md")):
        text = read(path)
        adr_text += text
        for heading in ("## Статус", "## Контекст", "## Варіанти", "## Рішення", "## Наслідки", "### Негативні"):
            check(heading in text, f"{path.name}: немає розділу «{heading}»")
    for nfr in sorted(nfr_ids):
        check(nfr in adr_text, f"R4: {nfr} не згадано в жодному ADR")

    quality = read(DOCS / "quality-scenarios.md")
    scenarios = re.findall(r"^## (QS-\d{2})\.", quality, re.MULTILINE)
    check(scenarios == ["QS-01", "QS-02"], f"Очікуються QS-01 і QS-02, знайдено {scenarios}")
    for element in ("Джерело стимулу", "Стимул", "Середовище", "Артефакт", "Реакція", "Вимірювана характеристика"):
        count = len(re.findall(rf"^\| {re.escape(element)} \|", quality, re.MULTILINE))
        check(count == 2, f"Елемент сценарію «{element}» має трапитися двічі, знайдено {count}")
    for block in quality.split("## QS-")[1:]:
        check("ADR-" in block, "Кожен сценарій має посилатися на ADR")


def validate_lab2() -> None:
    """Контрольний список здачі ЛР2 (виконується, якщо робота вже розпочата)."""
    if not (ROOT / "pipeline").exists():
        return
    required = [
        "pipeline/pipeline.py", "pipeline/requirements.txt", "results/encoding.csv",
        "docs/pipeline.md", "stream/package.sh", "stream/player.html",
        "stream/vendor/hls.min.js", "stream/vendor/dash.all.min.js", "stream/hls/master.m3u8",
        "results/qoe.csv", "docs/qoe.md",
    ]
    for name in required:
        check((ROOT / name).is_file(), f"ЛР2: немає файлу {name}")
    check(len(list((DOCS / "adr").glob("0004-*.md"))) == 1, "ЛР2: потрібен один ADR 0004-*.md")

    gitignore = read(ROOT / ".gitignore")
    for pattern in (".venv/", "data/", "stream/hls/**/*.ts", "stream/dash/*.m4s"):
        check(pattern in gitignore, f"ЛР2: .gitignore не виключає {pattern}")

    if (ROOT / "results/encoding.csv").is_file():
        rows = read(ROOT / "results/encoding.csv").strip().splitlines()[1:]
        codecs = sorted(row.split(",")[1] for row in rows)
        check(codecs == ["av1", "av1", "h264", "h264"], f"ЛР2: encoding.csv має містити 2×H.264 і 2×AV1, знайдено {codecs}")
    if (ROOT / "results/qoe.csv").is_file():
        lines = read(ROOT / "results/qoe.csv").strip().splitlines()
        check(lines[0] == "profile,startup_s,switches,stalls,stall_s,avg_kbps", "ЛР2: неправильний заголовок qoe.csv")
        profiles = [line.split(",")[0] for line in lines[1:]]
        for profile in ("П1", "П2", "П3"):
            check(profiles.count(profile) >= 2, f"ЛР2: профіль {profile} має бути виміряний щонайменше двічі")
    master = ROOT / "stream/hls/master.m3u8"
    if master.is_file():
        check(read(master).count("#EXT-X-STREAM-INF") == 3, "ЛР2: master.m3u8 має містити три рівні якості")
    for name, headings in (("docs/pipeline.md", ("## Вихідний матеріал", "## Конвеєр", "## Порівняння варіантів")),
                           ("docs/qoe.md", ("## Зв’язок з архітектурою",))):  # апостроф ’ — як у методичці
        if (ROOT / name).is_file():
            for heading in headings:
                check(heading in read(ROOT / name), f"ЛР2: {name} не містить розділу «{heading[3:]}»")


def validate_commit_count() -> None:
    result = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True)
    check(int(result.stdout.strip()) >= 2, "Історія має містити щонайменше два коміти")


def main() -> int:
    validate_required_files()
    validate_requirements()
    validate_correspondences()
    validate_adrs_and_scenarios()
    validate_lab2()
    if "--skip-git" not in sys.argv:
        validate_commit_count()
    if errors:
        print("Перевірку не пройдено:")
        for message in errors:
            print(f"  - {message}")
        return 1
    print("Перевірку пройдено: комплектність, вимоги, бюджет, правила відповідності R1–R5, ADR і сценарії")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
