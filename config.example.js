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
  units: "metric",          // "metric" (°C) or "imperial" (°F)

  clock24: true,            // false: 12-hour clock with am/pm
  seconds: true,            // the small seconds after the minutes
  locale: "",               // date language, e.g. "en-GB", "fr-FR"; "" follows the browser

  // Lava lamp background. The lamp button at the bottom right picks a mood or turns it off, and the
  // page remembers that pick; these are only the starting values. mood: "" drifts through all nine
  // over cycleHours, or name one: Nebula, Deep Sea, Aurora, Twilight, Ember, Rose Dusk,
  // Midnight Teal, Ultraviolet, Smoke & Ice. music: while Pear plays (nowPlaying.pear below), a
  // drifting lamp takes its colours from the album cover; false keeps it on the moods.
  // audio: "ws://127.0.0.1:9873" makes the wax move to the sound itself, if you run something there
  // that sends the text "bass mid high kick level" (five numbers, 0 to 1) many times a second.
  lava: { on: true, mood: "", music: true, cycleHours: 6, speed: 1, brightness: 1, fps: 30 },

  // The rain button next to the lamp (or the r key, unless a link uses it): steady rain with distant
  // thunder. false hides the button; { thunder: false } keeps the rain and drops the thunder.
  rain: true,

  // Optional "now playing" card. Endpoints that answer JSON, polled every 4 s:
  //   video: { id, title, author, url, cover } (obs-pear-remote's extras/serve.py serves /mpris.json)
  //   pear:  Pear Desktop's Amuse plugin, http://127.0.0.1:9863/query
  // null turns it off.
  nowPlaying: null,
};
