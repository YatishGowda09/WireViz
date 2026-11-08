# MachZero Hackathon — Team CrazyCoders

**Track:** Hardware  
**Repository:** [wireviz/WireViz](https://github.com/wireviz/WireViz)  
**Issue:** [#478 — How to create boxes to group connectors](https://github.com/wireviz/WireViz/issues/478)  
**Fork:** [YatishGowda09/WireViz](https://github.com/YatishGowda09/WireViz)  
**Branch:** `feature/issue-478-connector-grouping` (based on `dev`)

---

## Our Journey

### The First Hours: Searching for Direction

We entered the hackathon on the Hardware track knowing we wanted to contribute to something tangible — a tool that engineers and makers actually use. We shortlisted three open-source repositories:

- **[WLED](https://github.com/wled/WLED)** — LED strip controller firmware
- **[cocotb](https://github.com/cocotb/cocotb)** — Python-based hardware verification framework
- **[WireViz](https://github.com/wireviz/WireViz)** — Diagrams-as-Code for wiring harnesses

We spent the first few hours reading through each codebase, understanding their architectures and scanning their issue trackers. Some of these repositories had sparse documentation, which made onboarding slow. More critically, most of the interesting issues were either already claimed or too deeply coupled to domain-specific hardware knowledge we didn't have.

We couldn't find a viable, unclaimed issue until the last ten minutes before Round 1 began.

### Round 1: The Stumble

We found Issue #478  — a feature request from a sailboat owner asking WireViz to support visual grouping of connectors into physical device enclosures. The request resonated with us immediately; it was a real architectural gap that we felt we could address within the hackathon timeframe.

But by then, the Round 1 evaluation judges were already at our table.

We hadn't had time to prepare. We were still mentally processing the issue, the codebase, and the Graphviz rendering pipeline. When the judges asked us to explain the repository and our chosen issue. We couldn't articulate what WireViz was, or how we planned to solve it. The judges moved on quickly, we didn't get any questions to answer.

### The Reset: Lunch and Regrouping

After Round 1, we took a step back during the lunch break. Instead of spiraling, we made a deliberate decision: start over from scratch. No assumptions, no shortcuts.

Over the next hour, we methodically:

1. **Read the entire WireViz codebase** on the `dev` branch
2. **Understood the pipeline end-to-end** — from YAML input through Python domain objects to Graphviz DOT generation and final PNG/SVG/HTML output.
3. **Identified the exact architectural bottleneck** — the flat `self.connectors` dictionary in the `Harness` class and the unconditional root-level `dot.node()` emission in `create_graph()`.
4. **Designed a clean, backward-compatible solution** — introducing a `Group` dataclass and leveraging Graphviz's native `subgraph cluster_*` mechanism.

By the time we resurfaced, we had a working mental model of the entire system and a concrete implementation plan.

### Round 2 and Beyond

Round 2 evaluation was postponed due to time constraints. Rather than wait, we pushed forward into implementation — defining the data model, writing the YAML parser extensions, and modifying the graph construction logic to wrap grouped connectors inside Graphviz cluster subgraphs.

---

## What is WireViz?

WireViz is a **"Diagrams-as-Code"** tool for documenting cables, wiring harnesses, and connector pinouts. Engineers describe their wiring systems declaratively in plain YAML files:

```yaml
connectors:
  X1:
    type: D-Sub
    subtype: female
    pinlabels: [DCD, RX, TX, DTR, GND, DSR, RTS, CTS, RI]
  X2:
    type: Molex KK 254
    subtype: male
    pinlabels: [GND, RX, TX]

cables:
  W1:
    gauge: 0.25 mm2
    length: 0.5 m
    colors: [BK, RD, BU]

connections:
  -
    - X1: [5, 2, 3]
    - W1: [1, 2, 3]
    - X2: [1, 2, 3]
```

WireViz compiles this into:
- **Visual wiring diagrams** (PNG, SVG, HTML) with color-coded conductors and connector pinout tables
- **A manufacturing Bill of Materials** (BOM) with aggregated wire lengths, connector counts, and part numbers

The key value proposition: wiring documentation becomes version-controllable, diffable in Git, and automatable in CI pipelines — unlike binary CAD files or hand-drawn schematics.

---

## The Issue: #478

### The Real-World Problem

The issue author documents the electronics inside a sailboat. A boat's electrical system consists of distinct physical hardware units — an Autopilot computer, a chartplotter, instrument clusters, a battery distribution panel. Each unit is a single physical box with multiple connectors mounted on it (power, data, sensors, motors).

When these connectors are defined in WireViz, every connector becomes an isolated, floating entity on the diagram. There is no visual boundary indicating that five connectors all belong to the same Autopilot box. The diagram accurately shows pin-level wiring, but it completely fails to communicate the physical packaging of the system.

### Community Demand & Maintainer Support

Maintainers and users have been actively discussing this exact feature across multiple issues ([#478](https://github.com/wireviz/WireViz/issues/478), [#325](https://github.com/wireviz/WireViz/issues/325), and [#276](https://github.com/wireviz/WireViz/issues/276)) for over two years. Maintainer `@kvid` explicitly invited a community pull request with a clean syntax for grouping. 

We aren't working on an obscure edge case; we are solving one of the top three architectural gaps in the entire repository.

### Why WireViz Cannot Do This Today

WireViz's data model treats `Connector` as the highest-level visual entity. The `Harness` class stores all connectors in a flat dictionary (`self.connectors`) with no parent-child hierarchy. During graph generation, every connector node is emitted directly into the root Graphviz graph via `dot.node(...)`.

The only existing workaround requires injecting raw Graphviz DOT syntax into the `tweak.append` block:

```yaml
tweak:
  append: |
    subgraph cluster_autopilot {
      label = "Autopilot Unit"
      style = dashed
      "J1"
      "J2"
    }
```

This approach is brittle: it requires knowledge of Graphviz internals, bypasses all WireViz validation, and fails silently on connector name typos.

---

## Our Proposed Solution

### Core Idea

Introduce a first-class `groups:` section in the WireViz YAML schema that maps directly to Graphviz `subgraph cluster_*` blocks during graph generation.

```yaml
groups:
  autopilot:
    label: "Autopilot Unit"
    style: dashed
    color: "#336699"
    bgcolor: "#F4F7F9"
    members: [J1, J2]
```

### What Changes (Planned Code Snippets)

**1. Data Model (`wv_dataclasses.py`)**

Define the new `Group` domain entity:
```python
@dataclass
class Group:
    name: str
    label: Optional[str] = None
    style: Optional[str] = None
    color: Optional[SingleColor] = None
    bgcolor: Optional[SingleColor] = None
    members: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.label is None:
            self.label = self.name
        if self.color and not isinstance(self.color, SingleColor):
            self.color = SingleColor(self.color)
        if self.bgcolor and not isinstance(self.bgcolor, SingleColor):
            self.bgcolor = SingleColor(self.bgcolor)
```
In `Harness`: add `self.groups: Dict[str, Group] = {}` and an `add_group()` helper method.

**2. YAML Parser & Validation (`wireviz.py`)**

Parse the `groups:` section and fail fast on invalid member names:
```python
# In parse(): register and validate groups
if "groups" in yaml_data and isinstance(yaml_data["groups"], dict):
    for group_name, group_attrs in yaml_data["groups"].items():
        for member in group_attrs.get("members", []):
            if member not in harness.connectors and member not in harness.cables:
                raise ValueError(f"Group '{group_name}' references unknown member '{member}'")
        harness.add_group(name=group_name, **group_attrs)
```

**3. Graph Generator (`wv_harness.py`)**

Wrap grouped connector nodes in Graphviz cluster subgraphs inside `create_graph()`:
```python
# Inside Harness.create_graph()
# 1. Render connectors that belong to a group inside their respective cluster
for group in self.groups.values():
    with dot.subgraph(name=f"cluster_{group.name}") as cluster:
        cluster.attr(
            label=group.label,
            style=group.style or "solid",
            color=group.color.html if group.color else "#666666",
            bgcolor=group.bgcolor.html if group.bgcolor else "transparent",
            fontname=self.options.fontname,
        )
        for member_name in group.members:
            if member_name in self.connectors:
                conn = self.connectors[member_name]
                gv_html = gv_node_component(conn)
                cluster.node(conn.designator, label=f"<\n{gv_html}\n>", shape="box", style="filled")

# 2. Render ungrouped connectors at the root level (preserves 100% backward compatibility)
for conn in ungrouped_connectors:
    dot.node(conn.designator, label=f"<\n{gv_html}\n>", shape="box", style="filled")
```

**4. Documentation & Tests**
- Add automated regression tests in `tests/rendering/` verifying both grouped and ungrouped connectors.
- Document the new `groups:` schema in `docs/syntax.md`.

### Why This Works

- Graphviz has native support for `subgraph cluster_*` bounding boxes — we delegate all visual layout to the engine that already does it well.
- Users have already proven the visual result works via the `tweak.append` workaround in issues #276, #325, and #478. We are formalizing a battle-tested behavior into a validated, first-class feature.
- The change is purely additive. Existing YAML files without `groups:` produce identical output.

---

## What We Learned (The Hard Way)


**1. Graphviz is more powerful than it looks.**  
We initially worried that implementing visual grouping would require a custom rendering engine or SVG post-processing. Once we understood Graphviz's native `subgraph cluster_*` mechanism and confirmed that edges route seamlessly across cluster boundaries, the solution became dramatically simpler.

**2. The `tweak` hack was the proof-of-concept hiding in plain sight.**  
Multiple users across issues #276, #325, and #478 had already validated the visual output using raw `tweak.append` injections. Their workarounds served as empirical proof that Graphviz clusters produce the right diagrams. Our job was not to invent a new rendering approach, but to promote a proven one from an unvalidated string hack into a typed, validated, first-class citizen of WireViz's schema.

---

## Repository Structure (Key Files)

| File | Role |
|------|------|
| `src/wireviz/wv_dataclasses.py` | Domain model: `Connector`, `Cable`, `Group` (new), and component hierarchy |
| `src/wireviz/wireviz.py` | YAML parser, validator, and main entry point |
| `src/wireviz/wv_harness.py` | `Harness` class: orchestrates graph construction, BOM, and output |
| `src/wireviz/wv_graphviz.py` | Graphviz DOT node/edge builder, HTML table formatter, tweak engine |
| `src/wireviz/wv_bom.py` | Bill of Materials aggregation |
| `src/wireviz/wv_colors.py` | Industry-standard wire color engine (DIN 47100, IEC 60757) |
| `src/wireviz/wv_cli.py` | Click-based CLI (`wireviz harness.yml`) |
| `docs/syntax.md` | YAML syntax reference documentation |
| `tests/rendering/` | Rendering regression test YAML files |

---

## Team

**Team CrazyCoders** — MachZero Hackathon, Hardware Track

---
