// Start page settings. The installer copies this file to config.js; edit that copy, not this one.
// config.js is yours (git ignores it), so updates never overwrite it. Changes show on the next new tab.
window.STARTPAGE = {
  // [name, url, key]: the key opens the link when the page has focus (click it, or F6);
  // Shift+key opens it in a new tab, ? shows every key. Leave the key out ("") for none.
  links: [
    ["YouTube",   "https://www.youtube.com",   "y"],
    ["Gmail",     "https://mail.google.com",   "m"],
    ["Reddit",    "https://www.reddit.com",    "r"],
    ["GitHub",    "https://github.com",        "g"],
    ["Wikipedia", "https://en.wikipedia.org",  "w"],
    ["Hacker News", "https://news.ycombinator.com", "h"],
    ["Twitch",    "https://www.twitch.tv",     "t"],
    ["Claude",    "https://claude.ai",         "c"],
  ],

  // Weather from Open-Meteo (free, no account). A city name is looked up once and remembered;
  // for an exact spot use { name: "Home", lat: 48.85, lon: 2.35 }. null hides the widget.
  weather: { city: "London" },
  units: "metric",          // "metric" (°C, km/h) or "imperial" (°F, mph)

  clock24: true,            // false: 12-hour clock with am/pm
  seconds: true,            // the small seconds after the minutes
  locale: "",               // date language, e.g. "en-GB", "fr-FR"; "" follows the browser

  // Lava lamp background. The round button at the bottom right turns it on and off, and the page
  // remembers that; `on` is only the starting state. mood: "" drifts through all nine over
  // cycleHours, or name one: Nebula, Deep Sea, Aurora, Twilight, Ember, Rose Dusk,
  // Midnight Teal, Ultraviolet, Smoke & Ice.
  lava: { on: true, mood: "", cycleHours: 6, speed: 1, brightness: 1, fps: 30 },

  // Optional "now playing" card. Endpoints that answer JSON, polled every 4 s:
  //   video: { id, title, author, url, cover } (obs-pear-remote's extras/serve.py serves /mpris.json)
  //   pear:  Pear Desktop's Amuse plugin, http://127.0.0.1:9863/query
  // null turns it off.
  nowPlaying: null,
};
