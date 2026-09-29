#!/usr/bin/env python3
"""CI check, run after `install.py --city London`: did the install do its three jobs?
  check.py installed     settings, headlines, schedule (and that it fires), Firefox files,
                         and a headless Firefox that opens the page as its homepage
  check.py uninstalled   schedule and Firefox files are gone again
"""
import json, os, socket, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import install  # noqa: E402  (reuses its paths and Firefox detection)

failed = []


def check(ok, what):
    print(("  ok    " if ok else "  FAIL  ") + what, flush=True)
    if not ok:
        failed.append(what)


def sh(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def scheduled():
    if install.LINUX:
        return sh("systemctl", "--user", "is-enabled", f"{install.NAME}.timer").stdout.strip() == "enabled"
    if install.MAC:
        return sh("launchctl", "print", f"gui/{os.getuid()}/{install.launchd_plist().stem}").returncode == 0
    return sh("schtasks", "/Query", "/TN", install.NAME).returncode == 0


def fire_schedule():
    """Make the scheduler run news.py once, the way it will every 20 minutes."""
    if install.LINUX:
        sh("systemctl", "--user", "start", f"{install.NAME}.service")
    elif install.MAC:
        sh("launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{install.launchd_plist().stem}")
    else:
        sh("schtasks", "/Run", "/TN", install.NAME)


def firefox_exe(ff_dir):
    for name in ("firefox.exe", "firefox", "../MacOS/firefox"):
        p = ff_dir / name
        if p.exists():
            return str(p.resolve())
    raise FileNotFoundError(f"no firefox binary near {ff_dir}")


class Marionette:
    def __init__(self, exe, profile):
        self.ff = subprocess.Popen([exe, "--headless", "--no-remote", "--marionette", "--profile", str(profile)],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(120):
            try:
                self.sock = socket.create_connection(("127.0.0.1", 2828))
                break
            except OSError:
                time.sleep(0.5)
        else:
            raise RuntimeError("Marionette never came up")
        self.buf, self.id = b"", 0
        self.recv()

    def recv(self):
        while b":" not in self.buf:
            self.buf += self.sock.recv(65536)
        n, rest = self.buf.split(b":", 1)
        while len(rest) < int(n):
            rest += self.sock.recv(1 << 20)
        self.buf = rest[int(n):]
        return json.loads(rest[:int(n)])

    def cmd(self, name, params=None):
        self.id += 1
        data = json.dumps([0, self.id, name, params or {}]).encode()
        self.sock.sendall(str(len(data)).encode() + b":" + data)
        r = self.recv()
        if r[2]:
            raise RuntimeError(r[2])
        return r[3]

    def js(self, code):
        return self.cmd("WebDriver:ExecuteScript", {"script": code, "args": []})["value"]

    def quit(self):
        try:
            self.cmd("Marionette:Quit", {"flags": ["eForceQuit"]})
        except Exception:
            pass
        try:
            self.ff.wait(20)
        except subprocess.TimeoutExpired:
            self.ff.kill()


def installed():
    print("settings")
    cfg = ROOT / "config.js"
    check(cfg.exists() and 'city: "London"' in cfg.read_text(encoding="utf-8"), "config.js created with the city")
    check((ROOT / "feeds.json").exists(), "feeds.json created")

    print("headlines")
    news = ROOT / "news.js"
    check(news.exists(), "news.js written")
    if news.exists():
        data = json.loads(news.read_text(encoding="utf-8")[len("window.NEWS = "):].rstrip().rstrip(";"))
        filled = [k for k, v in data["tabs"].items() if v]
        check(len(filled) >= 3, f"at least 3 news tabs have headlines ({', '.join(filled)})")

    print("schedule")
    check(scheduled(), "news.py is scheduled")
    before = news.stat().st_mtime if news.exists() else 0
    time.sleep(1.5)
    fire_schedule()
    for _ in range(90):
        if news.exists() and news.stat().st_mtime > before:
            break
        time.sleep(1)
    check(news.exists() and news.stat().st_mtime > before, "the scheduled job runs and rewrites news.js")

    print("firefox")
    dirs, notes = install.firefox_dirs()
    for n in notes:
        print("  note  " + n)
    check(bool(dirs), f"found Firefox ({', '.join(map(str, dirs))})")
    if not dirs:
        return
    ff = dirs[0]
    for rel in ("mozilla.cfg", "defaults/pref/autoconfig.js"):
        p = ff / rel
        check(p.exists() and install.MARK in p.read_text(encoding="utf-8"), f"{rel} written")
    profile = Path(os.environ.get("RUNNER_TEMP", ROOT)) / "ff-profile"
    profile.mkdir(exist_ok=True)
    m = Marionette(firefox_exe(ff), profile)
    try:
        m.cmd("WebDriver:NewSession", {})
        url = ""
        for _ in range(20):
            url = m.cmd("WebDriver:GetCurrentURL")["value"]
            if url.startswith("file:"):
                break
            time.sleep(0.5)
        check(url == install.PAGE.as_uri(), f"Firefox starts on the page ({url})")
        time.sleep(3)
        links = m.js("return document.querySelectorAll('#links a').length")
        tabs = m.js("return [...document.querySelectorAll('#tabs button')].map(b => b.dataset.tab)")
        cards = m.js("return document.querySelectorAll('#cards .card').length")
        check(links == 8, f"the page shows the example's 8 links ({links})")
        check(len(tabs) >= 3 and cards > 0, f"the page shows news tabs and cards ({tabs}, {cards} cards)")
        m.cmd("WebDriver:SetWindowRect", {"width": 1600, "height": 900})
        time.sleep(3)
        out = Path(os.environ.get("RUNNER_TEMP", ROOT)) / "startpage.png"
        import base64
        out.write_bytes(base64.b64decode(m.cmd("WebDriver:TakeScreenshot", {"full": False})["value"]))
        print(f"  saved {out}")
    finally:
        m.quit()


def uninstalled():
    check(not scheduled(), "schedule removed")
    for d in install.firefox_dirs()[0]:
        for rel in ("mozilla.cfg", "defaults/pref/autoconfig.js"):
            check(not (d / rel).exists(), f"{d / rel} removed")


if __name__ == "__main__":
    {"installed": installed, "uninstalled": uninstalled}[sys.argv[1]]()
    if failed:
        sys.exit(f"{len(failed)} check(s) failed")
    print("all good")
