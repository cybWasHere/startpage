#!/usr/bin/env python3
"""Fetch RSS/Atom headlines into news.js next to the start page (window.NEWS = {...}).
A file:// page can load a local <script> but can't fetch feeds (no CORS), hence the file.
Items without a feed image (HN) get the article's og:image, cached in og-cache.json.
Feeds come from feeds.json (or feeds.example.json until you make one). install.py schedules
this every 20 minutes; run it by hand to refresh now."""
import html, json, os, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "news.js")
OG_CACHE = os.path.join(HERE, "og-cache.json")
FEEDS_FILES = [os.path.join(HERE, "feeds.json"), os.path.join(HERE, "feeds.example.json")]
A = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"
DC = "{http://purl.org/dc/elements/1.1/}"
UA = {"User-Agent": "Mozilla/5.0 startpage-news"}
WEB = re.compile(r"https?://", re.I)


def get(url, limit=None):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read(limit) if limit else r.read()


def when(s):
    if not s:
        return 0
    try:
        return parsedate_to_datetime(s).timestamp()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0


def text(s, n=320, tags=True):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or "") if tags else s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def first_img(s):
    m = re.search(r'<img[^>]+src="([^"]+)"', s or "")
    return html.unescape(m.group(1)) if m else ""


def parse_item(it):
    desc_raw = it.findtext("description", "")
    img = ""
    for tag in (MEDIA + "content", MEDIA + "thumbnail"):
        el = it.find(tag)
        if el is not None and el.get("url"):
            img = el.get("url")
            break
    enc = it.find("enclosure")
    if not img and enc is not None and enc.get("type", "").startswith("image"):
        img = enc.get("url", "")
    item = {"title": it.findtext("title", ""), "url": it.findtext("link", ""),
            "t": when(it.findtext("pubDate")), "img": img or first_img(desc_raw),
            "desc": text(desc_raw), "author": it.findtext(DC + "creator", "")}
    comments = it.findtext("comments", "")
    if "news.ycombinator.com" in comments:  # hnrss: description is just points/comments
        pts = re.search(r"Points: (\d+)", desc_raw)
        com = re.search(r"# Comments: (\d+)", desc_raw)
        item["desc"] = ""
        item["stats"] = f"{pts.group(1) if pts else '?'} points · {com.group(1) if com else '?'} comments"
        item["comments"] = comments
        item["site"] = re.sub(r"^www\.", "", urllib.parse.urlsplit(item["url"]).hostname or "")
    return item


def parse_entry(it):
    link = it.find(A + "link[@rel='alternate']")
    if link is None:
        link = it.find(A + "link")
    body = it.findtext(A + "summary", "") or it.findtext(A + "content", "")
    return {"title": it.findtext(A + "title", ""), "url": link.get("href", "") if link is not None else "",
            "t": when(it.findtext(A + "published") or it.findtext(A + "updated")),
            "img": first_img(it.findtext(A + "content", "") or body), "desc": text(body),
            "author": it.findtext(f"{A}author/{A}name", ""),
            "tags": [c.get("term") for c in it.findall(A + "category") if c.get("term")][:3]}


def fetch(source, url):
    root = ET.fromstring(get(url))
    items = [parse_item(i) for i in root.iter("item")] + [parse_entry(e) for e in root.iter(A + "entry")]
    for i in items:
        i["title"] = text(i["title"], 400, tags=False)  # a title is plain text: "Vec<T>" is not a tag
        i["src"] = source
        i["url"] = i["url"].strip()
        if not WEB.match(i.get("comments", "")):  # the page opens these: nothing but web links
            i.pop("comments", None)
    return [i for i in items if i["title"] and WEB.match(i["url"])]


def og_image(url):
    try:
        page = get(url, 200_000).decode("utf-8", "replace")
    except Exception:
        return ""
    for pat in (r'<meta[^>]+(?:property|name)="(?:og:image|twitter:image)"[^>]+content="([^"]+)"',
                r'<meta[^>]+content="([^"]+)"[^>]+(?:property|name)="(?:og:image|twitter:image)"'):
        m = re.search(pat, page)
        if m:
            return urllib.parse.urljoin(url, html.unescape(m.group(1)))
    return ""


def fill_images(items):
    try:
        with open(OG_CACHE, encoding="utf-8") as f:
            cache = json.load(f)
    except (OSError, ValueError):
        cache = {}
    todo = [i["url"] for i in items if not i["img"] and i["url"] not in cache]
    with ThreadPoolExecutor(8) as ex:
        for url, img in zip(todo, ex.map(og_image, todo)):
            cache[url] = img
    for i in items:
        if not i["img"]:
            i["img"] = cache.get(i["url"], "")
    keep = {i["url"] for i in items}
    with open(OG_CACHE, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in cache.items() if k in keep}, f)


def load_feeds():
    path = next(p for p in FEEDS_FILES if os.path.exists(p))
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["tabs"], cfg.get("perTab", 8)


def main():
    if sys.stderr:  # None under pythonw, which is how the Windows task runs this
        sys.stderr.reconfigure(errors="replace")  # feed errors may hold characters a Windows console can't show
    tabs, per_tab = load_feeds()
    news = {}
    for tab, feeds in tabs.items():
        items = []
        share = -(-per_tab // max(len(feeds), 1))  # equal share per source so a busy feed can't fill the tab
        for source, url in feeds:
            try:
                items += sorted(fetch(source, url), key=lambda i: i["t"], reverse=True)[:share]
            except Exception as e:  # one dead feed shouldn't blank the tab
                print(f"{source}: {e}", file=sys.stderr)
        items.sort(key=lambda i: i["t"], reverse=True)
        news[tab] = items[:per_tab]
    if not any(news.values()):
        sys.exit("no feed answered; keeping the old news.js")
    fill_images([i for tab in news.values() for i in tab])
    data = {"updated": datetime.now(timezone.utc).timestamp(), "tabs": news}
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("window.NEWS = " + json.dumps(data, ensure_ascii=False) + ";\n")
    os.replace(tmp, OUT)


if __name__ == "__main__":
    main()
