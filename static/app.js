// Sound alerts: OFF by default, never plays on page load by itself.
// It plays only if the user switched it on AND a warning banner is shown after a user action.
(function () {
  var KEY = "gh-sound";
  var btn = document.getElementById("sound-toggle");
  var audio = document.getElementById("alert-sound");
  var label = document.getElementById("sound-label");
  var use = btn ? btn.querySelector("use") : null;
  function enabled() { try { return localStorage.getItem(KEY) === "on"; } catch (e) { return false; } }
  function paint() {
    if (!btn) return;
    var on = enabled();
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    label.textContent = on ? "Sound alerts: on" : "Sound alerts: off";
    use.setAttribute("href", "/static/icons.svg#" + (on ? "i-bell" : "i-bell-off"));
  }
  function play() { if (audio) { audio.currentTime = 0; var p = audio.play(); if (p && p.catch) p.catch(function () {}); } }
  if (btn) btn.addEventListener("click", function () {
    try { localStorage.setItem(KEY, enabled() ? "off" : "on"); } catch (e) {}
    paint();
    if (enabled()) play();            // short preview, triggered by the user's click
  });
  paint();
  if (enabled() && document.querySelector('[data-alert="1"]')) play();
})();
