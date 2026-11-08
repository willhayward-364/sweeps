"""Shared page layout: header with menu, page title and footer version banner.

Every page is wrapped by render_page() so they all look and behave the same.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from version import get_version_banner

STYLESHEET = Path(__file__).with_name("style.css")


def stylesheet_href() -> str:
    """style.css with a short fingerprint of its contents, e.g. style.css?v=1a2b3c4d.

    Browsers and preview sites cache the stylesheet; changing the URL whenever the
    file changes makes them fetch the new version instead of using an old copy.
    """
    try:
        fingerprint = hashlib.md5(STYLESHEET.read_bytes()).hexdigest()[:8]
        return f"style.css?v={fingerprint}"
    except OSError:
        return "style.css"

NAV_ITEMS = [
    ("index.html", "Standings"),
    ("form.html", "Form"),
    ("players.html", "Players"),
    ("latest_results.html", "Results"),
    ("upcoming_fixtures.html", "Fixtures"),
    ("prizes.html", "Prizes"),
    ("rules.html", "Rules"),
    ("shame.html", "Hall of Shame"),
]

# Easter egg: tap the LSB logo 10 times in quick succession and it turns into
# the Tottenham crest (for this browser session). Another 10 taps turn it back.
EASTER_EGG_TAPS = 10
EASTER_EGG_CREST = "images/crests/england_tottenham.football-logos.cc.png"


def render_topbar(active_page: str = "") -> str:
    link_lines = []
    for href, label in NAV_ITEMS:
        if href == active_page:
            link_lines.append(f'      <a href="{href}" class="nav-btn active" aria-current="page">{label}</a>')
        else:
            link_lines.append(f'      <a href="{href}" class="nav-btn">{label}</a>')
    links = "\n".join(link_lines)
    return f"""
  <header class="topbar">
    <div class="topbar-brand">
      <img src="images/crests/LSB_crest.PNG" alt="Sweepstake Logo" class="topbar-logo" id="site-logo">
      <strong>LSB Official Agreed Sweepstake</strong>
    </div>
    <nav class="nav-links">
{links}
    </nav>
  </header>
  <script>
    (function () {{
      var logo = document.getElementById("site-logo");
      if (!logo) return;
      var original = logo.getAttribute("src");
      var egg = "{EASTER_EGG_CREST}";
      var taps = 0, timer = null;
      function show(on, animate) {{
        logo.src = on ? egg : original;
        logo.alt = on ? "Tottenham Hotspur crest" : "Sweepstake Logo";
        logo.classList.toggle("logo-egg", on);
        if (animate) {{
          logo.classList.remove("logo-spin");
          void logo.offsetWidth;
          logo.classList.add("logo-spin");
        }}
      }}
      var active = false;
      try {{ active = sessionStorage.getItem("spursLogo") === "1"; }} catch (e) {{}}
      if (active) show(true, false);
      logo.addEventListener("click", function () {{
        taps += 1;
        clearTimeout(timer);
        timer = setTimeout(function () {{ taps = 0; }}, 1500);
        if (taps >= {EASTER_EGG_TAPS}) {{
          taps = 0;
          active = !active;
          show(active, true);
          try {{ sessionStorage.setItem("spursLogo", active ? "1" : "0"); }} catch (e) {{}}
        }}
      }});
    }})();
  </script>"""


# Easter egg game: tap the faint ball in the footer to play keepy-uppy.
KEEPY_UPPY = """
  <div class="game-overlay" hidden>
    <div class="game-box">
      <div class="game-head">
        <span class="game-title">Keepy-Uppy</span>
        <span class="game-score">0</span>
        <button type="button" class="game-close" aria-label="Close game">✕</button>
      </div>
      <div class="game-stage">
        <canvas class="game-canvas" width="320" height="420"></canvas>
        <div class="game-over" hidden>
          <div class="game-over-label">Score</div>
          <div class="game-over-score">0</div>
          <div class="game-over-note"></div>
          <button type="button" class="game-again">Play again</button>
        </div>
      </div>
      <div class="game-foot"><span class="game-msg">Tap the ball to start</span><span class="muted game-best"></span></div>
    </div>
  </div>
  <script>
    // Keepy-uppy: tap the ball to kick it up; score a point per touch; game over when it hits the floor.
    (function () {
      function init() {
        var opener = document.querySelector(".egg-ball"), overlay = document.querySelector(".game-overlay");
        if (!opener || !overlay || overlay.dataset.ready) return;
        overlay.dataset.ready = "1";
        var canvas = overlay.querySelector(".game-canvas"), ctx = canvas.getContext("2d");
        var scoreEl = overlay.querySelector(".game-score"), msg = overlay.querySelector(".game-msg");
        var bestEl = overlay.querySelector(".game-best");
        var overPanel = overlay.querySelector(".game-over");
        var overScore = overlay.querySelector(".game-over-score"), overNote = overlay.querySelector(".game-over-note");
        var W = canvas.width, H = canvas.height, R = 26, GRAVITY = 0.35;
        // state: "ready" (ball waiting to be tapped), "playing", or "over" (dropped; next tap resets)
        var ball, score, best = 0, state = "ready", running = false, frame = null;
        try { best = parseInt(localStorage.getItem("keepyUppyBest") || "0", 10) || 0; } catch (e) {}

        function reset() {
          ball = { x: W / 2, y: H * 0.35, vx: 0, vy: 0, spin: 0 };
          score = 0; state = "ready"; scoreEl.textContent = "0"; overPanel.hidden = true;
          bestEl.textContent = best ? "Best " + best : "";
          msg.textContent = "Tap the ball to start";
        }

        function draw() {
          ctx.clearRect(0, 0, W, H);
          ctx.fillStyle = "#2f9e44";                       // pitch strip
          ctx.fillRect(0, H - 18, W, 18);
          ctx.strokeStyle = "rgba(255,255,255,0.5)";
          ctx.beginPath(); ctx.moveTo(0, H - 18); ctx.lineTo(W, H - 18); ctx.stroke();
          ctx.save();
          ctx.translate(ball.x, ball.y); ctx.rotate(ball.spin);
          ctx.font = (R * 2) + "px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
          ctx.fillText("⚽", 0, 2);
          ctx.restore();
        }

        function step() {
          if (state === "playing") {
            ball.vy += GRAVITY; ball.x += ball.vx; ball.y += ball.vy; ball.spin += ball.vx * 0.03;
            if (ball.x < R) { ball.x = R; ball.vx = Math.abs(ball.vx) * 0.8; }
            if (ball.x > W - R) { ball.x = W - R; ball.vx = -Math.abs(ball.vx) * 0.8; }
            if (ball.y > H - 18 - R) {                      // hit the floor
              ball.y = H - 18 - R; state = "over";
              var newBest = score > best;
              if (newBest) { best = score; try { localStorage.setItem("keepyUppyBest", String(best)); } catch (e) {} }
              overScore.textContent = String(score);
              overNote.textContent = newBest ? "New best! 🎉" : "Best: " + best;
              overPanel.hidden = false;
              msg.textContent = "Dropped it!";
              bestEl.textContent = "Best " + best;
            }
          }
          draw();
          if (running) frame = requestAnimationFrame(step);
        }

        function kick(evt) {
          evt.preventDefault();
          var box = canvas.getBoundingClientRect();
          var x = (evt.clientX - box.left) * (W / box.width), y = (evt.clientY - box.top) * (H / box.height);
          if (state === "over") return;                      // use the Play again button
          var dx = ball.x - x, dy = ball.y - y;
          if (dx * dx + dy * dy <= (R * 1.6) * (R * 1.6)) {   // a generous hit area
            if (state === "ready") { state = "playing"; msg.textContent = "Keep it up!"; }
            ball.vy = -9 - Math.min(score * 0.08, 3);         // gets a little livelier as you go
            ball.vx = dx * 0.18 + (Math.random() - 0.5) * 2;
            score += 1; scoreEl.textContent = String(score);
          }
        }

        function open() {
          overlay.hidden = false; reset();
          if (!running) { running = true; frame = requestAnimationFrame(step); }
        }
        function close() { overlay.hidden = true; running = false; if (frame) cancelAnimationFrame(frame); }

        opener.addEventListener("click", open);
        overlay.querySelector(".game-close").addEventListener("click", close);
        overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });
        canvas.addEventListener("pointerdown", kick);
        overlay.querySelector(".game-again").addEventListener("click", reset);
      }
      if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
    })();
  </script>"""


# Optional extra HTML shown under the menu on every page (e.g. a celebration banner).
# fetch_and_score.py sets this before building the pages.
SITE_BANNER = ""


def render_page(
    *,
    page: str,
    title: str,
    heading: str,
    body: str,
    output_path: str | Path,
    version: str | None = None,
) -> None:
    """Writes a complete page: header, title, body content, then the version banner footer."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="stylesheet" href="{stylesheet_href()}">
</head>
<body>
  {render_topbar(page)}{SITE_BANNER}
  <main>
  <h1 class="page-title visually-hidden">{heading}</h1>
{body}
  </main>
  <footer class="site-footer">
    {get_version_banner(version=version)}
    <button type="button" class="egg-ball" aria-label="Play keepy-uppy">⚽</button>
  </footer>{KEEPY_UPPY}
</body>
</html>
"""
    Path(output_path).write_text(html, encoding="utf-8")
