"""Read the cached series of native Word charts inside a .docx (no Excel needed)."""
import re, zipfile
from lxml import etree

NS = {"c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}

def _text(nodes):
    return "".join(nodes)

def read_charts(docx_path):
    out = {}
    with zipfile.ZipFile(docx_path) as z:
        for name in z.namelist():
            m = re.fullmatch(r"word/charts/chart(\d+)\.xml", name)
            if not m:
                continue
            root = etree.fromstring(z.read(name))
            title = _text(root.xpath(".//c:title//a:t/text()", namespaces=NS))
            series = []
            for ser in root.findall(".//c:ser", NS):
                sname = _text(ser.xpath("./c:tx//c:v/text()", namespaces=NS))
                # first-level categories only (multi-level caches list tier labels first)
                cats = ser.xpath("./c:cat//c:lvl[1]/c:pt/c:v/text()", namespaces=NS) or \
                       ser.xpath("./c:cat//c:pt/c:v/text()", namespaces=NS)
                vals = [float(v) for v in ser.xpath("./c:val//c:pt/c:v/text()", namespaces=NS)]
                series.append({"name": sname, "cats": list(cats), "vals": vals})
            out[int(m.group(1))] = {"title": title, "series": series}
    return out
