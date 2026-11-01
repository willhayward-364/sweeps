"""Shared page layout: header with menu, page title and footer version banner.

Every page is wrapped by render_page() so they all look and behave the same.
"""
from __future__ import annotations

from pathlib import Path

from version import get_version_banner

NAV_ITEMS = [
    ("index.html", "Standings"),
    ("form.html", "Form"),
    ("players.html", "Players"),
    ("latest_results.html", "Results"),
    ("upcoming_fixtures.html", "Fixtures"),
    ("rules.html", "Rules"),
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
  <link rel="stylesheet" href="style.css">
</head>
<body>
  {render_topbar(page)}
  <main>
  <h1 class="page-title visually-hidden">{heading}</h1>
{body}
  </main>
  <footer class="site-footer">
    {get_version_banner(version=version)}
  </footer>
</body>
</html>
"""
    Path(output_path).write_text(html, encoding="utf-8")
