"""Render clean SVG diagrams without external dependencies.

The Mermaid files in docs/diagrams remain the editable source. This fallback
renderer mirrors the same architecture with deterministic orthogonal routing.
All connectors terminate on node borders and nodes are painted above routes.
"""

from html import escape
from pathlib import Path


OUT = Path(__file__).resolve().parents[1] / "docs" / "diagrams"


class Svg:
    def __init__(self, width: int, height: int, title: str):
        self.width = width
        self.height = height
        self.base = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
            "<defs>",
            '<marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#526273"/></marker>',
            '<marker id="arrowStart" markerWidth="10" markerHeight="10" refX="1" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M9,0 L9,6 L0,3 z" fill="#526273"/></marker>',
            '<filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-opacity="0.14"/></filter>',
            "</defs>",
            '<rect width="100%" height="100%" fill="#f8fafc"/>',
            f'<text x="{width/2}" y="34" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="24" font-weight="700" fill="#17324d">{escape(title)}</text>',
        ]
        self.routes = []
        self.nodes = []
        self.labels = []

    def cluster(self, x, y, w, h, label, fill="#ffffff", stroke="#94a3b8"):
        self.base.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        self.base.append(f'<text x="{x+18}" y="{y+30}" font-family="Segoe UI,Arial,sans-serif" font-size="18" font-weight="700" fill="#334155">{escape(label)}</text>')

    def node(self, x, y, w, h, lines, fill="#eef6ff", stroke="#245a8d"):
        self.nodes.append('<g filter="url(#shadow)">')
        self.nodes.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        line_height = 20
        first_y = y + h / 2 - (len(lines) - 1) * line_height / 2 + 6
        for index, line in enumerate(lines):
            self.nodes.append(f'<text x="{x+w/2}" y="{first_y+index*line_height}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="15" fill="#172033">{escape(line)}</text>')
        self.nodes.append("</g>")

    def path(self, points, label=None, label_at=None, dashed=False, bidirectional=False):
        coords = " ".join(f"{x},{y}" for x, y in points)
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        start = ' marker-start="url(#arrowStart)"' if bidirectional else ""
        self.routes.append(f'<polyline points="{coords}" fill="none" stroke="#526273" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" marker-end="url(#arrow)"{start}{dash}/>')
        if label:
            if label_at is None:
                p1, p2 = points[len(points)//2-1], points[len(points)//2]
                label_at = ((p1[0]+p2[0])/2, (p1[1]+p2[1])/2)
            lx, ly = label_at
            width = max(66, len(label) * 7.2)
            self.labels.append(f'<rect x="{lx-width/2}" y="{ly-15}" width="{width}" height="21" rx="5" fill="#f8fafc" stroke="#e2e8f0"/>')
            self.labels.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" font-family="Segoe UI,Arial,sans-serif" font-size="12" fill="#334155">{escape(label)}</text>')

    def save(self, path: Path):
        content = self.base + self.routes + self.nodes + self.labels + ["</svg>"]
        path.write_text("\n".join(content), encoding="utf-8")


def render_context():
    s = Svg(1700, 900, "Контекстне подання розумної парковки")
    s.cluster(30, 65, 360, 790, "Зацікавлені сторони", "#f1f7ff", "#7aa7d1")
    s.cluster(1310, 65, 360, 790, "Зовнішні системи", "#fff9e9", "#c4972e")
    left = [(95,120,["Водій"]),(95,300,["Оператор парковки"]),(95,480,["Адміністратор","/ технічна служба"]),(95,660,["Служба безпеки"])]
    right = [(1380,190,["Payment Service"]),(1380,410,["Navigation Service"]),(1380,630,["Notification Service"])]
    s.path([(355,155),(480,155),(480,255),(600,255)], "запит місць / статус і маршрут", (480,145), bidirectional=True)
    s.path([(355,335),(500,335),(500,375),(600,375)], "ручне керування / стан", (480,325), bidirectional=True)
    s.path([(355,515),(500,515),(500,525),(600,525)], "конфігурація / метрики", (465,505), bidirectional=True)
    s.path([(355,695),(480,695),(480,645),(600,645)], "пошук / події інцидентів", (475,685), bidirectional=True)
    s.path([(1100,280),(1220,280),(1220,225),(1380,225)], "сесія / результат оплати", (1240,270), bidirectional=True)
    s.path([(1100,445),(1240,445),(1380,445)], "координати / маршрут", (1240,435), bidirectional=True)
    s.path([(1100,610),(1220,610),(1220,665),(1380,665)], "повідомлення", (1230,600))
    for x, y, lines in left:
        s.node(x, y, 260, 70, lines)
    for x, y, lines in right:
        s.node(x, y, 220, 70, lines, "#fff4d6", "#9a6b00")
    s.node(600,180,500,540,["Система розумної парковки","моніторинг місць, доступ, навігація"],"#dff3e4","#237a3b")
    s.save(OUT / "context.svg")


def render_components():
    s = Svg(2400, 1120, "Компонентне подання розумної парковки")
    s.cluster(30,60,300,1015,"Джерела","#f1f7ff","#7aa7d1")
    s.cluster(360,60,690,1015,"Периферійне оброблення","#effaf1","#65a978")
    s.cluster(1080,60,760,1015,"Серверні компоненти","#f7f2ff","#9473c5")
    s.cluster(1870,60,500,1015,"Клієнти та актуатори","#fff8ed","#c4972e")
    s.path([(290,155),(390,155)],"H.264/RTSP",(340,145))
    s.path([(630,155),(690,155)],"ознаки",(660,110))
    s.path([(930,155),(980,155)],"синхронні дані",(955,285))
    s.path([(1040,190),(1120,190)],"стан місця",(1080,180))
    s.path([(1360,190),(1900,190)],"актуальна карта",(1630,180))
    s.path([(290,375),(390,375)],"1 Гц",(340,365))
    s.path([(630,375),(690,375)],"MQTT QoS 1",(660,330))
    s.path([(930,375),(955,375),(955,225),(980,225)],"відліки",(950,300))
    s.path([(1360,190),(1395,190),(1395,375),(1430,375)],"дозвіл",(1395,285))
    s.path([(1670,375),(1900,375)],"команда",(1785,365))
    s.path([(290,575),(390,575)],"JPEG",(340,565))
    s.path([(630,575),(690,575)],"OCR + confidence",(660,520))
    s.path([(930,575),(1120,575)],"подія з ID",(1025,565))
    s.path([(1360,575),(1430,575)],"межі сесії",(1395,520))
    s.path([(1670,575),(1900,575)],"ідемпотентний запит",(1785,565))
    s.path([(1360,225),(1415,225),(1415,755),(1430,755)],"стан зон",(1415,690))
    s.path([(1670,755),(1900,755)],"напрямок",(1785,745))
    s.path([(1300,225),(1300,290),(1740,290),(1740,875),(1900,875)],"API",(1740,850))
    s.path([(1900,895),(1790,895),(1790,375),(1670,375)],"ручне керування",(1790,650))
    s.path([(1240,225),(1100,225),(1100,860),(1210,860),(1210,895)],"метадані",(1100,840))
    s.path([(630,155),(660,155),(660,755),(690,755)],"відеокадри",(660,700))
    s.path([(510,610),(510,820),(810,820),(810,790)],"кадри номерів",(650,810))
    s.path([(930,755),(1060,755),(1060,1060),(1380,1060),(1380,1017),(1430,1017)],"подійні фрагменти",(1220,1070))
    s.path([(1240,225),(1240,340)],"конфігурація",(1240,285))
    s.path([(1360,375),(1375,375),(1375,1017),(1330,1017)],"стан пристроїв",(1375,850),dashed=True)
    s.path([(1550,410),(1720,410),(1720,930),(1670,930)],"аудит",(1720,850))
    s.path([(1360,575),(1400,575),(1400,930),(1430,930)],"аудит",(1400,850))
    s.path([(810,410),(960,410),(960,1025),(1090,1025)],"метрики",(1020,1015),dashed=True)
    s.path([(1120,190),(1080,190),(1080,1017),(1090,1017)],"метрики API",(1080,700),dashed=True)
    for x,y,label in [(70,120,"IP Cameras"),(70,340,"Ultrasonic Sensors"),(70,540,"LPR Camera")]:
        s.node(x,y,220,70,[label])
    for x,y,label,fill,stroke in [
        (390,120,"Video Analytics","#dff3e4","#237a3b"),(690,120,"Time Synchronizer","#dff3e4","#237a3b"),
        (390,340,"Sensor Ingest","#dff3e4","#237a3b"),(690,340,"MQTT Broker","#dff3e4","#237a3b"),
        (390,540,"LPR Service","#dff3e4","#237a3b"),(690,540,"Local Event Buffer","#fff4d6","#9a6b00")]:
        s.node(x,y,240,70,[label],fill,stroke)
    s.node(980,120,60,140,["Occupancy","Fusion"],"#dff3e4","#237a3b")
    s.node(690,720,240,70,["Local Video Buffer"],"#fff4d6","#9a6b00")
    for x,y,label in [(1120,155,"Parking API"),(1120,340,"Device Registry"),(1430,340,"Access Service"),(1120,540,"Session Service"),(1430,540,"Payment Adapter"),(1430,720,"Guidance Service")]:
        s.node(x,y,240,70,[label],"#f3eaff","#6941a5")
    s.node(1090,895,240,70,["Metadata DB"],"#fff4d6","#9a6b00")
    s.node(1430,895,240,70,["Audit Log"],"#fff4d6","#9a6b00")
    s.node(1090,990,240,55,["Observability"],"#f3eaff","#6941a5")
    s.node(1430,990,240,55,["Event Media Storage"],"#fff4d6","#9a6b00")
    for x,y,label,fill,stroke in [
        (1900,155,"Driver App","#ffe8e8","#a23a3a"),(1900,340,"Gate Controller","#eef6ff","#245a8d"),
        (1900,540,"Payment Service","#fff4d6","#9a6b00"),(1900,720,"Information Board","#eef6ff","#245a8d"),
        (1900,840,"Operator Dashboard","#ffe8e8","#a23a3a")]:
        s.node(x,y,400,70,[label],fill,stroke)
    s.save(OUT / "components.svg")


def render_deployment():
    s = Svg(2500,1150,"Подання розгортання розумної парковки")
    s.cluster(30,60,330,1040,"Польові пристрої","#f1f7ff","#7aa7d1")
    s.cluster(390,60,680,1040,"Edge-вузол парковки","#effaf1","#65a978")
    s.cluster(1100,60,800,1040,"Серверний сегмент","#f7f2ff","#9473c5")
    s.cluster(1930,60,540,1040,"Клієнти та актуатори","#fff8ed","#c4972e")

    s.path([(320,160),(430,160)],"RTSP",(375,150))
    s.path([(320,335),(430,335)],"RTSP/JPEG",(375,325))
    s.path([(320,520),(370,520),(370,625),(430,625)],"MQTT QoS 1",(370,570))
    s.path([(710,155),(830,155),(830,465),(790,465)],"ознаки",(830,300))
    s.path([(710,315),(810,315),(810,495),(790,495)],"OCR",(810,390))
    s.path([(580,590),(580,530)],"відліки",(620,570))
    s.path([(430,505),(400,505),(400,765),(430,765)],"події",(365,650))
    s.path([(710,155),(1045,155),(1045,765),(1040,765)],"відеокадри",(1045,600))
    s.path([(710,315),(1055,315),(1055,785),(1040,785)],"кадри номерів",(1055,690))
    s.path([(570,800),(570,825),(650,825),(650,850)],"події",(610,815))
    s.path([(900,800),(900,825),(810,825),(810,850)],"фрагменти",(855,815))
    s.path([(870,885),(1080,885),(1080,155),(1160,155)],"TLS: події та фрагменти",(1080,500))

    s.path([(1320,190),(1320,280)],"HTTPS",(1320,240))
    s.path([(1500,190),(1500,230),(1675,230),(1675,280)],"HTTPS",(1600,220))
    s.path([(1305,350),(1305,450)],"API",(1305,405))
    s.path([(1675,350),(1675,400),(1500,400),(1500,450)],"API",(1585,390))
    s.path([(1350,540),(1350,680)],"метадані",(1350,615))
    s.path([(1650,540),(1650,680)],"медіа",(1650,615))
    s.path([(1750,495),(1870,495),(1870,935),(1640,935)],"метрики й аудит",(1870,800))
    s.path([(870,1015),(1090,1015),(1090,935),(1300,935)],"метрики",(1090,990),dashed=True)

    s.path([(1660,155),(1980,155)],"HTTPS",(1820,145),bidirectional=True)
    s.path([(1980,335),(1880,335),(1880,90),(1580,90),(1580,120)],"HTTPS",(1880,220),bidirectional=True)
    s.path([(1750,495),(1860,495),(1860,515),(1980,515)],"ідемпотентні запити",(1860,485),bidirectional=True)
    s.path([(730,625),(1050,625),(1050,1080),(1910,1080),(1910,715),(1980,715)],"локальна MQTT-команда",(1500,1070))
    s.path([(790,485),(1070,485),(1070,1050),(1900,1050),(1900,895),(1980,895)],"стан зон",(1500,1040))
    s.path([(1980,355),(1920,355),(1920,1065),(1060,1065),(1060,645),(730,645)],"аварійне керування",(1500,1055))

    s.node(70,120,250,80,["IP Cameras","50 × H.264, 1080p, 15 FPS"])
    s.node(70,295,250,80,["LPR Camera","в'їзд / виїзд"])
    s.node(70,480,250,80,["Sensor Controllers","500 датчиків"])

    s.node(430,120,280,70,["Video Analytics"],"#dff3e4","#237a3b")
    s.node(430,280,280,70,["LPR Service"],"#dff3e4","#237a3b")
    s.node(430,440,360,90,["Sensor Ingest + Time Synchronizer","+ Occupancy Fusion"],"#dff3e4","#237a3b")
    s.node(430,590,300,70,["MQTT Broker"],"#dff3e4","#237a3b")
    s.node(430,730,280,70,["Local Event Buffer"],"#fff4d6","#9a6b00")
    s.node(760,730,280,70,["Local Video Buffer","2 ТБ / 12 год"],"#fff4d6","#9a6b00")
    s.node(590,850,280,70,["Sync Agent"],"#dff3e4","#237a3b")
    s.node(590,980,280,70,["Local Metrics"],"#dff3e4","#237a3b")

    s.node(1160,120,500,70,["Reverse Proxy / Load Balancer"],"#f3eaff","#6941a5")
    s.node(1140,280,330,70,["Parking API instance 1"],"#f3eaff","#6941a5")
    s.node(1510,280,330,70,["Parking API instance 2"],"#f3eaff","#6941a5")
    s.node(1250,450,500,90,["Access Service, Session Service,","Guidance Service, Device Registry,","Payment Adapter"],"#f3eaff","#6941a5")
    s.node(1140,680,300,70,["Metadata DB"],"#fff4d6","#9a6b00")
    s.node(1500,680,320,70,["Event Media Storage","не менше 8 ТБ"],"#fff4d6","#9a6b00")
    s.node(1300,900,340,70,["Observability + Audit Log"],"#f3eaff","#6941a5")

    for x,y,label,fill,stroke in [
        (1980,120,"Driver App","#ffe8e8","#a23a3a"),(1980,300,"Operator Dashboard","#ffe8e8","#a23a3a"),
        (1980,480,"Payment Service","#fff4d6","#9a6b00"),(1980,680,"Gate Controller","#eef6ff","#245a8d"),
        (1980,860,"Information Board","#eef6ff","#245a8d")]:
        s.node(x,y,420,70,[label],fill,stroke)
    s.save(OUT / "deployment.svg")


if __name__ == "__main__":
    render_context()
    render_components()
    render_deployment()
    print("Rendered context.svg, components.svg and deployment.svg")
