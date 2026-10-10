"""Validate the laboratory repository without external dependencies."""

from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DIAGRAMS = ROOT / "docs" / "diagrams"
SVG_NS = "{http://www.w3.org/2000/svg}"


def fail(message: str) -> None:
    raise AssertionError(message)


def validate_required_files() -> None:
    required = [
        "README.md",
        "docs/requirements.md",
        "docs/quality-scenarios.md",
        "docs/adr/0001-edge-processing.md",
        "docs/adr/0002-data-transport.md",
        "docs/adr/0003-event-storage.md",
    ]
    required += [f"docs/diagrams/{name}.{suffix}" for name in ("context", "components", "deployment") for suffix in ("mmd", "svg")]
    missing = [name for name in required if not (ROOT / name).is_file()]
    if missing:
        fail(f"Missing required files: {', '.join(missing)}")


def validate_requirements() -> None:
    text = (ROOT / "docs" / "requirements.md").read_text(encoding="utf-8")
    functional = set(re.findall(r"^### (FR-\d{2})\.", text, re.MULTILINE))
    nonfunctional = set(re.findall(r"^\| (NFR-\d{2}) \|", text, re.MULTILINE))
    if len(functional) != 10:
        fail(f"Expected 10 functional requirements, found {len(functional)}")
    if len(nonfunctional) != 6:
        fail(f"Expected 6 non-functional requirements, found {len(nonfunctional)}")
    matrix = text.split("## 12. Матриця трасовності", maxsplit=1)[-1]
    for requirement_id in sorted(functional | nonfunctional):
        if not re.search(rf"^\| {re.escape(requirement_id)} \|", matrix, re.MULTILINE):
            fail(f"Requirement is absent from the traceability matrix: {requirement_id}")


def validate_adrs_and_quality_scenarios() -> None:
    adr_headings = ("## Статус", "## Контекст", "## Варіанти", "## Рішення", "## Наслідки", "### Негативні")
    for path in sorted((ROOT / "docs" / "adr").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for heading in adr_headings:
            if heading not in text:
                fail(f"{path.name}: missing section {heading}")

    quality = (ROOT / "docs" / "quality-scenarios.md").read_text(encoding="utf-8")
    scenarios = re.findall(r"^## (QS-\d{2})\.", quality, re.MULTILINE)
    if scenarios != ["QS-01", "QS-02"]:
        fail(f"Expected QS-01 and QS-02, found {scenarios}")
    for element in (
        "Джерело стимулу",
        "Стимул",
        "Середовище",
        "Артефакт",
        "Реакція",
        "Вимірювана характеристика",
    ):
        if len(re.findall(rf"^\| {re.escape(element)} \|", quality, re.MULTILINE)) != 2:
            fail(f"Quality scenarios must contain {element} twice")
    for scenario in quality.split("## QS-")[1:]:
        if "ADR-" not in scenario:
            fail("Each quality scenario must reference an ADR")


def segment_crosses_rect(p1, p2, rect) -> bool:
    x1, y1 = p1
    x2, y2 = p2
    rx, ry, rw, rh = rect
    if x1 == x2:
        return rx < x1 < rx + rw and max(min(y1, y2), ry) < min(max(y1, y2), ry + rh)
    if y1 == y2:
        return ry < y1 < ry + rh and max(min(x1, x2), rx) < min(max(x1, x2), rx + rw)
    fail(f"Non-orthogonal connector segment: {p1} -> {p2}")


def validate_svg(path: Path) -> None:
    root = ET.parse(path).getroot()
    node_rects = []
    label_rects = []
    for rect in root.findall(f".//{SVG_NS}rect"):
        if rect.get("rx") == "10":
            node_rects.append(tuple(float(rect.get(name, "0")) for name in ("x", "y", "width", "height")))
        elif rect.get("rx") == "5":
            label_rects.append(tuple(float(rect.get(name, "0")) for name in ("x", "y", "width", "height")))
    for polyline in root.findall(f".//{SVG_NS}polyline"):
        points = [tuple(float(value) for value in token.split(",")) for token in polyline.get("points", "").split()]
        for p1, p2 in zip(points, points[1:]):
            for rect in node_rects:
                if segment_crosses_rect(p1, p2, rect):
                    fail(f"{path.name}: connector {p1} -> {p2} crosses node {rect}")
    for lx, ly, lw, lh in label_rects:
        for nx, ny, nw, nh in node_rects:
            if max(lx, nx) < min(lx + lw, nx + nw) and max(ly, ny) < min(ly + lh, ny + nh):
                fail(f"{path.name}: connector label {(lx, ly, lw, lh)} overlaps node {(nx, ny, nw, nh)}")


def validate_diagram_names() -> None:
    expected = {
        "components.svg": ("Device Registry", "Local Video Buffer", "Occupancy", "Fusion"),
        "deployment.svg": ("Local Video Buffer", "Parking API instance 1", "Parking API instance 2", "Event Media Storage"),
    }
    for filename, names in expected.items():
        text = (DIAGRAMS / filename).read_text(encoding="utf-8")
        for name in names:
            if name not in text:
                fail(f"{filename}: missing architecture element {name}")


def validate_commit_count() -> None:
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    count = int(result.stdout.strip())
    if count < 2:
        fail(f"Expected at least 2 commits, found {count}")


def main() -> int:
    validate_required_files()
    validate_requirements()
    validate_adrs_and_quality_scenarios()
    for name in ("context.svg", "components.svg", "deployment.svg"):
        validate_svg(DIAGRAMS / name)
    validate_diagram_names()
    if "--skip-git" not in sys.argv:
        validate_commit_count()
    print("Validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
