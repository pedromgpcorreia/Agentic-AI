"""Builds slides/deck.html, a standalone copy of the deck, from slides/src (open it in a browser)."""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
BLOBS = {"1e919c68d9f3e300673492cb8d6edb1a": "baseline.png", "fb4d6c76d8eab9b1fe0959d555c1114f": "baseline_sens.png",
         "73fffa5938e981f2ef4c160cbcea41fe": "calibration.png", "8e30a4fe1d7b1580e557ff2d4eaa8847": "profit.png",
         "e910f4d8a4041042460e250ce3b59f1c": "learned.png", "9b7b7ff43a7b8ef136fb4ba983d6b3ce": "digi.png",
         "595a58fc5a03e177b394268013d5a5d3": "sensitivity.png", "21303b77947db2fc056299cc4cfef437": "live_clean.gif"}
deck = json.load(open(f"{HERE}/src/deck.json", encoding="utf8"))
html = ('<!doctype html><meta charset="utf-8"><title>' + deck["title"] + '</title>'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400..700'
        '&family=IBM+Plex+Sans:wght@400;500;600&display=swap"><style>*{margin:0;box-sizing:border-box}'
        'section{width:1920px;height:1080px;position:relative;overflow:hidden;border-bottom:4px solid #999}aside{display:none}'
        'table{border-collapse:collapse;width:100%}td,th{padding:.35em .6em;border-bottom:1px solid #bbb;text-align:left}'
        'x-shape{display:block;clip-path:polygon(0 30%,60% 30%,60% 0,100% 50%,60% 100%,60% 70%,0 70%)}ul{padding-left:1.2em}'
        '</style><script>const f=()=>document.documentElement.style.zoom=innerWidth/1920;addEventListener("resize",f);f()</script>')
for sid in deck["order"]:
    text = open(f"{HERE}/src/slides/{sid}.html", encoding="utf8").read()
    html += re.sub(r"/_blob/(\w+)", lambda m: "assets/" + BLOBS[m.group(1)], text)
open(f"{HERE}/deck.html", "w", encoding="utf8").write(html)
