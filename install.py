#!/usr/bin/env python3
"""Set up the start page on Linux, macOS or Windows. Python 3.8+, nothing to pip install.

    python3 install.py               install or update (Windows: py install.py)
    python3 install.py --uninstall   undo it; your config.js and feeds.json stay

It does three things, and running it again is harmless:
  1. creates config.js and feeds.json from the examples, if you don't have them yet;
  2. fetches the headlines now, and schedules news.py every 20 minutes
     (a systemd user timer, a launchd agent, or a Windows scheduled task);
  3. makes the page Firefox's new tab and homepage through Firefox's autoconfig: two small files
     in Firefox's install folder, which needs admin rights (it asks).
"""
import argparse, json, os, re, shlex, shutil, subprocess, sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
PAGE = HERE / "index.html"
NEWS = HERE / "news.py"
NAME = "startpage-news"
MARK = "github.com/cybWasHere/startpage"  # in every Firefox file we write; we never touch files without it
LINUX, MAC, WIN = sys.platform.startswith("linux"), sys.platform == "darwin", os.name == "nt"


def say(msg, kind="*"):
    print(f" {kind} {msg}", flush=True)


def run(*cmd, check=True):
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


# 1. config -------------------------------------------------------------------------------------

def make_configs(city):
    for mine, example in (("config.js", "config.example.js"), ("feeds.json", "feeds.example.json")):
        if (HERE / mine).exists():
            say(f"{mine} already there, left as is")
            continue
        text = (HERE / example).read_text(encoding="utf-8")
        if mine == "config.js":
            if city is None and sys.stdin.isatty():
                city = input("   City for the weather (Enter for London, - for none): ").strip() or "London"
            if city == "-":
                text = re.sub(r"weather: \{ city: \"London\" \},", "weather: null,", text)
            elif city:
                text = text.replace('city: "London"', "city: " + json.dumps(city))
        (HERE / mine).write_text(text, encoding="utf-8")
        say(f"created {mine}, edit it to make the page yours", "+")


# 2. headlines ----------------------------------------------------------------------------------

def fetch_now():
    r = subprocess.run([sys.executable, str(NEWS)], capture_output=True, text=True, errors="replace")
    for line in (r.stderr or "").strip().splitlines():
        say(f"news.py: {line}", "!")
    say("headlines fetched" if r.returncode == 0 else "no headlines yet; the schedule will retry", "+" if r.returncode == 0 else "!")


def write_fresh(path, text, **kw):
    """Replace the file itself: an old `systemctl link` symlink would otherwise be written through."""
    path.unlink(missing_ok=True)
    path.write_text(text, **kw)


def quiet_python():
    """On Windows, pythonw.exe runs without flashing a console window every 20 minutes."""
    exe = Path(sys.executable)
    if WIN and exe.with_name("pythonw.exe").exists():
        return str(exe.with_name("pythonw.exe"))
    return str(exe)


def systemd_dir():
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "systemd" / "user"


def launchd_plist():
    return Path.home() / "Library" / "LaunchAgents" / f"io.github.cybwashere.{NAME}.plist"


def schedule():
    if LINUX:
        if not shutil.which("systemctl") or run("systemctl", "--user", "show-environment", check=False).returncode:
            say("no systemd user session. Add this to `crontab -e` instead:", "!")
            print(f"     */20 * * * * {shlex.quote(sys.executable)} {shlex.quote(str(NEWS))}")
            return
        d = systemd_dir()
        d.mkdir(parents=True, exist_ok=True)
        write_fresh(d / f"{NAME}.service",
            f"[Unit]\nDescription=Refresh start page headlines (news.js)\nAfter=network-online.target\n\n"
            f"[Service]\nType=oneshot\nExecStart=\"{sys.executable}\" \"{NEWS}\"\n")
        write_fresh(d / f"{NAME}.timer",
            "[Unit]\nDescription=Refresh start page headlines every 20 minutes\n\n"
            "[Timer]\nOnBootSec=1min\nOnUnitActiveSec=20min\nPersistent=true\n\n"
            "[Install]\nWantedBy=timers.target\n")
        run("systemctl", "--user", "daemon-reload")
        run("systemctl", "--user", "disable", f"{NAME}.timer", check=False)  # drops stale enable links
        run("systemctl", "--user", "enable", "--now", f"{NAME}.timer")
        say(f"systemd user timer {NAME}.timer runs news.py every 20 minutes", "+")
    elif MAC:
        p = launchd_plist()
        p.parent.mkdir(parents=True, exist_ok=True)
        label = p.stem
        write_fresh(p, f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key><array><string>{escape(sys.executable)}</string><string>{escape(str(NEWS))}</string></array>
  <key>StartInterval</key><integer>1200</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardErrorPath</key><string>{escape(str(HERE / "news.log"))}</string>
</dict></plist>
""")
        domain = f"gui/{os.getuid()}"
        run("launchctl", "bootout", f"{domain}/{label}", check=False)
        r = run("launchctl", "bootstrap", domain, str(p), check=False)
        if r.returncode:
            run("launchctl", "load", "-w", str(p), check=False)
        say(f"launchd agent {label} runs news.py every 20 minutes", "+")
    elif WIN:
        xml = HERE / f"{NAME}.xml"
        # XML rather than schtasks flags: the flags can't say "also run on battery" or "catch up after sleep"
        xml.write_text(f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Refresh start page headlines ({MARK})</Description></RegistrationInfo>
  <Triggers>
    <TimeTrigger><StartBoundary>2026-01-01T00:00:00</StartBoundary><Enabled>true</Enabled>
      <Repetition><Interval>PT20M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition></TimeTrigger>
  </Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author"><Exec>
    <Command>{escape(quiet_python())}</Command>
    <Arguments>"{escape(str(NEWS))}"</Arguments>
    <WorkingDirectory>{escape(str(HERE))}</WorkingDirectory>
  </Exec></Actions>
</Task>
""", encoding="utf-16")
        try:
            run("schtasks", "/Create", "/F", "/TN", NAME, "/XML", str(xml))
        finally:
            xml.unlink()
        say(f"scheduled task {NAME} runs news.py every 20 minutes", "+")


def unschedule():
    if LINUX and shutil.which("systemctl"):
        run("systemctl", "--user", "disable", "--now", f"{NAME}.timer", check=False)
        for ext in ("service", "timer"):
            (systemd_dir() / f"{NAME}.{ext}").unlink(missing_ok=True)
        run("systemctl", "--user", "daemon-reload", check=False)
    elif MAC:
        p = launchd_plist()
        run("launchctl", "bootout", f"gui/{os.getuid()}/{p.stem}", check=False)
        p.unlink(missing_ok=True)
    elif WIN:
        run("schtasks", "/Delete", "/F", "/TN", NAME, check=False)
    say("headline schedule removed", "-")


# 3. Firefox ------------------------------------------------------------------------------------

def firefox_dirs():
    """Firefox install folders (the ones holding omni.ja), plus notes on Firefoxes autoconfig can't reach."""
    cands, notes = [], []
    if LINUX:
        cands += [Path(p) for p in ("/usr/lib/firefox", "/usr/lib64/firefox", "/usr/lib/firefox-esr",
                                    "/usr/lib64/firefox-esr", "/opt/firefox", "/usr/lib/firefox-developer-edition")]
        exe = shutil.which("firefox")
        if exe:
            real = Path(exe).resolve()
            if "/snap/" in str(real) or real.name == "snap":
                notes.append("Snap Firefox (Ubuntu's default) is read-only, so autoconfig can't go in.")
            cands.append(real.parent)
        if shutil.which("flatpak") and run("flatpak", "info", "org.mozilla.firefox", check=False).returncode == 0:
            notes.append("Flatpak Firefox is read-only, so autoconfig can't go in.")
    elif MAC:
        for root in (Path("/Applications"), Path.home() / "Applications"):
            for app in ("Firefox.app", "Firefox Developer Edition.app", "Firefox Nightly.app"):
                cands.append(root / app / "Contents" / "Resources")
    elif WIN:
        for env in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            if os.environ.get(env):
                cands.append(Path(os.environ[env]) / "Mozilla Firefox")
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Mozilla\Mozilla Firefox") as k:
                ver = winreg.QueryValueEx(k, "CurrentVersion")[0]
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Mozilla\Mozilla Firefox\{ver}\Main") as k:
                cands.append(Path(winreg.QueryValueEx(k, "Install Directory")[0]))
        except OSError:
            pass
    seen, dirs = set(), []
    for d in cands:
        try:
            key = d.resolve()
        except OSError:
            continue
        if key not in seen and (d / "omni.ja").exists() and "/snap/" not in str(key):
            seen.add(key)
            dirs.append(d)
    return dirs, notes


def autoconfig_files(page_uri):
    pref = (f"// {MARK}: points Firefox at mozilla.cfg\n"
            'pref("general.config.filename", "mozilla.cfg");\n'
            'pref("general.config.obscure_value", 0);\n'
            'pref("general.config.sandbox_enabled", false);\n')
    cfg = (f"// {MARK}: new tab + homepage (Firefox skips this first line)\n"
           f"const STARTPAGE = {json.dumps(page_uri)};\n"
           'defaultPref("browser.startup.homepage", STARTPAGE);  // new windows + home button\n'
           "try {\n"
           '  const { AboutNewTab } = ChromeUtils.importESModule("resource:///modules/AboutNewTab.sys.mjs");\n'
           "  AboutNewTab.newTabURL = STARTPAGE;  // Ctrl+T and the + button\n"
           "} catch (e) { Cu.reportError(e); }\n")
    return {Path("defaults/pref/autoconfig.js"): pref, Path("mozilla.cfg"): cfg}


def ours(path):
    try:
        return MARK in path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return True
    except OSError:
        return False


def write_firefox(ff_dir, page_uri, force):
    """Runs with admin rights when the folder needs them. Returns 0 on success."""
    files = {ff_dir / rel: text for rel, text in autoconfig_files(page_uri).items()}
    if all(p.exists() and p.read_text(encoding="utf-8", errors="replace") == t for p, t in files.items()):
        say(f"Firefox at {ff_dir} is already set up")
        return 0
    foreign = [p for p in files if not ours(p)]
    if foreign and not force:
        for p in foreign:
            say(f"{p} exists and isn't ours; left alone. Rerun with --force to replace it (a .bak is kept).", "!")
        return 1
    for p, text in files.items():
        if p in foreign:
            shutil.copy2(p, p.with_name(p.name + ".bak"))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    say(f"Firefox at {ff_dir} opens the page on new tabs and at start", "+")
    return 0


def remove_firefox(ff_dir):
    for rel in autoconfig_files("").keys():
        p = ff_dir / rel
        if p.exists() and ours(p):
            p.unlink()
            bak = p.with_name(p.name + ".bak")
            if bak.exists():
                bak.replace(p)
    say(f"autoconfig removed from {ff_dir}", "-")
    return 0


def elevated(args):
    """Rerun this script with admin rights for one Firefox folder; returns its exit code."""
    me = [sys.executable, str(Path(__file__).resolve())] + args
    if WIN:
        ps_args = " ".join('"' + a.replace('"', '\\"') + '"' for a in me[1:])
        ps = (f"$p = Start-Process -Verb RunAs -Wait -PassThru -WindowStyle Hidden "
              f"-FilePath '{me[0].replace(chr(39), chr(39) * 2)}' -ArgumentList '{ps_args.replace(chr(39), chr(39) * 2)}'; exit $p.ExitCode")
        say("Windows will ask for admin rights to write into Firefox's folder")
        return subprocess.run(["powershell", "-NoProfile", "-Command", ps]).returncode
    say("writing into Firefox's folder needs sudo")
    return subprocess.run(["sudo"] + me).returncode


def firefox(uninstall, force, only_dir=None):
    """Returns how many Firefox folders couldn't be set up."""
    dirs, notes = firefox_dirs()
    if only_dir:
        dirs = [Path(only_dir)]
    for n in notes:
        say(n + " See the README for the manual way.", "!")
    if not dirs:
        if not notes:
            say("no Firefox found; set the page as your homepage by hand (see the README)", "!")
        return 0
    uri = PAGE.as_uri()
    failed = 0
    for d in dirs:
        try:
            rc = remove_firefox(d) if uninstall else write_firefox(d, uri, force)
        except PermissionError:
            args = ["--firefox-dir", str(d)] + (["--uninstall"] if uninstall else []) + (["--force"] if force else [])
            rc = elevated(args)
            if rc and MAC:
                say("macOS may block it: allow your terminal under System Settings › Privacy & Security › "
                    "App Management, then run this again.", "!")
        failed += rc != 0
        if rc == 0 and not uninstall:
            say("restart Firefox completely (quit it, not just close the window) to see it", ">")
    return failed


def main():
    for stream in (sys.stdout, sys.stderr):  # a Windows console or pipe may be cp1252; never crash on a path or a feed name
        if stream:
            stream.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--uninstall", action="store_true", help="remove the schedule and the Firefox files")
    ap.add_argument("--city", help="city for the weather when creating config.js (- for none)")
    ap.add_argument("--no-firefox", action="store_true", help="leave Firefox alone")
    ap.add_argument("--force", action="store_true", help="replace a mozilla.cfg that some other tool wrote (keeps a .bak)")
    ap.add_argument("--firefox-dir", help=argparse.SUPPRESS)  # the elevated rerun: only touch this folder
    a = ap.parse_args()

    if a.firefox_dir:
        d = Path(a.firefox_dir)
        sys.exit(remove_firefox(d) if a.uninstall else write_firefox(d, PAGE.as_uri(), a.force))

    if a.uninstall:
        print("Removing the start page setup", flush=True)
        unschedule()
        if not a.no_firefox:
            firefox(True, False)
        say("config.js, feeds.json and this folder are still here; delete the folder to finish")
        return

    print(f"Setting up the start page in {HERE}", flush=True)
    make_configs(a.city)
    fetch_now()
    schedule()
    if not a.no_firefox and firefox(False, a.force):
        sys.exit(f"\nFirefox isn't set up, see above. The page itself: {PAGE.as_uri()}")
    print(f"\nDone. The page itself: {PAGE.as_uri()}")


if __name__ == "__main__":
    main()
