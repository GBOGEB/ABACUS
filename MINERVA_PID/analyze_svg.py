#!/usr/bin/env python3
"""Analyze P&ID SVG files: dimensions, elements, colors, text, structure."""
import re, sys, os, json
from collections import Counter
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
INK_NS = "http://www.inkscape.org/namespaces/inkscape"

def localname(tag):
    return tag.split('}')[-1] if '}' in tag else tag

def analyze(path):
    size = os.path.getsize(path)
    tree = ET.parse(path)
    root = tree.getroot()
    info = {"file": os.path.basename(path), "path": path, "size_bytes": size}

    # root attributes
    info["viewBox"] = root.get("viewBox")
    info["width"] = root.get("width")
    info["height"] = root.get("height")
    docname = root.get("{%s}docname" % "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd")
    info["docname"] = docname

    # element counts
    tag_counter = Counter()
    for el in root.iter():
        tag_counter[localname(el.tag)] += 1
    info["total_elements"] = sum(tag_counter.values())
    info["tag_counts"] = dict(tag_counter.most_common())

    # inkscape layers (groups with inkscape:groupmode=layer)
    layers = []
    for el in root.iter():
        if localname(el.tag) == 'g':
            gm = el.get("{%s}groupmode" % INK_NS)
            if gm == 'layer':
                label = el.get("{%s}label" % INK_NS)
                layers.append(label or el.get('id'))
    info["layers"] = layers

    # text content
    texts = []
    for el in root.iter():
        if localname(el.tag) in ('text', 'tspan'):
            if el.text and el.text.strip():
                texts.append(el.text.strip())
    info["text_count"] = len(texts)
    info["sample_texts"] = texts[:60]

    # colors - parse fill/stroke from style attrs and direct attrs
    color_counter = Counter()
    hexpat = re.compile(r'#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}')
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    for m in hexpat.findall(content):
        color_counter[m.lower()] += 1
    info["unique_colors"] = len(color_counter)
    info["top_colors"] = color_counter.most_common(25)

    # named colors in stroke/fill
    info["path_d_count"] = content.count('<path') + content.count(' d=')
    return info

if __name__ == "__main__":
    results = []
    for p in sys.argv[1:]:
        results.append(analyze(p))
    print(json.dumps(results, indent=2, ensure_ascii=False))
