# MINERVA CryoCell P&ID v3 — Default Views Guide

Each v3 SVG embeds five named **default-view presets** as machine-readable
metadata (`<metadata>` → `minerva:defaultViews`). A view is simply a list of
which layers are visible, letting a reviewer declutter the drawing to a single
purpose with one toggle set. The presets are documented here and can be applied
in Inkscape (Layers panel) or by a small script that flips each layer's
`display` attribute.

### How the presets are stored

```xml
<metadata id="minerva-pid-meta">
  <minerva:defaultViews xmlns:minerva="https://sckcen.be/minerva/pid">
    <view name="DEFAULT_FULL">
      <layer name="00_Background_TitleBlock" visible="true"/>
      ...
    </view>
    ...
  </minerva:defaultViews>
</metadata>
```

### The five views

| View | Purpose | What is shown |
|------|---------|---------------|
| **DEFAULT_FULL** | Complete drawing for normal review | All layers except the legend overlay (legend is opt-in) |
| **DEFAULT_PROCESS** | Process / piping focus | Background, scope, structures, all piping (primary+branch+secondary+outside), valves, sensors, tags |
| **DEFAULT_CONTROL** | Instrumentation & control focus | Background, scope, sensors, DIS/control, the three signal layers, out-of-scope services, tags |
| **DEFAULT_MAIN** | Main-line schematic (declutter) | Background, scope, equipment, only the three **PRIMARY** cryo trunks + secondary water + valves + tags |
| **PRINT_MONO** | Black-and-white plotting | All layers except the legend overlay; use the `_MONO` file variant |

### Applying a view in Inkscape

1. Open the SVG → **Object ▸ Layers…** (Shift+Ctrl+L).
2. Toggle the eye icon for each layer per the table above, **or**
3. Run the helper below to write a view-specific copy.

```python
import re, sys
svg = open(sys.argv[1]).read()
VISIBLE = {  # paste the layer list for the chosen view
    "00_Background_TitleBlock", "01_Scope_Boundaries", "03_Equipment_Vessels",
    "04A_Piping_PRIMARY_40K", "05A_Piping_PRIMARY_4p5K", "06A_Piping_PRIMARY_2K",
    "07_Piping_SECONDARY_Water", "09_Valves_Mechanical", "15_Tags_Instruments",
}
def repl(m):
    name = m.group(1)
    disp = "inline" if name in VISIBLE else "none"
    return f'id="{name}" inkscape:label="{name}" style="display:{disp}"'
out = re.sub(r'id="([^"]+)" inkscape:label="[^"]+" style="display:[^"]+"', repl, svg)
open(sys.argv[1].replace(".svg", "_VIEW.svg"), "w").write(out)
```

### The toggleable legend & notes

* **`16_Legend_TOGGLEABLE`** is shipped **hidden** so the drawing area is
  maximised. Turn it on for hand-off prints or when sharing with new reviewers.
* **`17_Notes_TOGGLEABLE`** (buffer volumes, scope hand-over notes, control
  callouts) is shipped **visible** but can be hidden for a clean schematic.
