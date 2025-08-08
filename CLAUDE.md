Sweet — here’s a **ready-to-drop-in `CLAUDE.md` for V2** plus a **tight prompt** you can paste into your coding agent to get the work done exactly to spec.

---

# CLAUDE.md (V2)

## Project

**Data Center Pipe Sizer** — internal MEP tool to size chilled/condenser water piping, risers, and chillers using early-phase inputs (MW, ΔT, fluid, velocity). V1 exists and runs via CLI & Gradio; V2 expands UX, layout modeling, riser logic, charts, and cloud-readiness.

## Branch

Work in **`v2`** branch. Keep `main` stable; V2 deploys to a separate Render service (or switch branch in Render when approved).

## High-Level Goals (V2)

1. **Charts render on Render** inside the Gradio app (no `plt.show()`; return figures).
2. **Layout-driven multi–data-hall modeling** via `C×R×F` (Columns × Rows × Floors).
3. **Per-hall loads** (or uniform load) + **Fan Heat %**.
4. **Riser modeling**: shared risers per column (default) vs independent per hall; placement markers for viz.
5. **Visualizations**:

   * Velocity vs Pipe ID
   * ΔP vs Pipe ID (psi per 100 ft)
   * Building layout heatmap (MW per hall)
   * Riser stack loads (GPM per column + recommended nominal size)
6. **Polish**: velocity warnings; normalize ΔP/100 ft; tables clean and readable.
7. **Cloud-ready**: Gradio binds to `0.0.0.0:$PORT`; requirements pinned; Render deploy docs.

## Current Repo (relevant)

* `main.py` — `pipeline_sizing()` (Imperial units, velocity/ΔP sizing, nominal lookup hooked elsewhere)
* `calc/fluid_properties.py` — water/EG properties `(ρ, μ)` in Imperial
* `calc/pipe_lookup.py` — nominal vs ID lookup (STD/40)
* `data/Standard_Pipe_Schedule.csv` — IDs for STD pipe
* `chiller_sizing.py` — top-3 configs table (simple strategy + redundancy)
* `gradio_app.py` — cloud UI already patched to bind to `0.0.0.0:$PORT`

## New/Changed Modules (V2)

Create:

* `calc/layout.py`

  * `parse_layout(spec: str) -> tuple[int,int,int]`  # “2x2x3” → (cols, rows, floors); validate ≥1
  * `make_hall_names(cols:int, rows:int, floors:int, include_floors=False) -> list[str]`

    * If `include_floors=False`: names = `DH-C{c}-R{r}`
    * If `include_floors=True`: names = `DH-C{c}-R{r}-F{f}`
  * `column_aggregates(cols:int, rows:int, floors:int, per_hall_mw: list[float]) -> list[float]`

    * Returns per-column **total MW** across floors (shared-riser mode)
* `calc/visualization.py`

  * `velocity_figure(ids_in: list[float], velocities_fps: list[float], gpm: float) -> go.Figure`
  * `dp_figure(ids_in: list[float], dpps_psi_per_100ft: list[float], subtitle:str=\"\") -> go.Figure`
  * `layout_heatmap(cols:int, rows:int, hall_mw_matrix: list[list[float]], riser_side:str) -> go.Figure`
  * `riser_stack_bar(stacks_gpm: list[float], labels: list[str], recommended_sizes: list[str]) -> go.Figure`

Update:

* `gradio_app.py` — add inputs/outputs; return plotly figures to `gr.Plot()` components; compute layout/riser results.

## Functional Details

### Units (Imperial)

* Input load per hall in **MW**. Convert to **BTU/hr** then to **lb/hr** using Cp ≈ **1.0 BTU/lb·°F**.
* Density **lb/ft³**, viscosity **lb/ft·s**.
* Velocity **ft/s**, diameter output **inches**, ΔP in **psi per 100 ft**.

### Layout Semantics

* Input format: `C×R×F` = **Columns × Rows × Floors**.
* **Total halls** = `C * R * F`.
* **Default**: show distinct hall names per (C,R) (not per-floor) = `DH-C{c}-R{r}`.

  * Toggle: *Include floors in hall names* → `DH-C{c}-R{r}-F{f}`.

### Per-Hall MW + Fan Heat

* Toggle: **Use same MW for all halls** (default ON).

  * If ON → single number input: `default_hall_mw`.
  * If OFF → show an editable DataFrame with columns: `["Data Hall", "IT Load (MW)"]`.
* Fan heat input `%` (0–20). Effective hall cooling load:

  ```
  hall_cooling_mw = it_mw * (1 + fan_pct/100)
  ```

### Riser Sharing & Placement

* Toggle: **Shared risers among halls?** (default ON).

  * If ON: **one riser stack per column** across all floors:

    * Sum MW for each column across floors → convert to GPM → size a pipe per stack (same velocity & ΔP/100ft constraints).
    * Output a per-stack table: Column label, Total GPM, Nominal Size, Velocity, ΔP/100ft.
  * If OFF: size each hall independently (optionally aggregate per column for a summary).
* Riser placement dropdown for visualization marker only (no hydraulics in V2):

  * Choices: “West”, “East”, “North”, “South”, “NW corner”, “NE corner”, “SW corner”, “SE corner”.

### Charts (must render on Render)

Use **Plotly** and **return the `go.Figure` objects** from the callback.

* Velocity vs Pipe ID
* ΔP vs Pipe ID (psi per 100 ft)
* Layout heatmap (MW per hall)
* Riser stack bar chart (GPM with size labels)

### Pipe ΔP normalization

* Show ΔP as **psi per 100 ft**. Internally either fix length=100 ft for the calc or compute dp/ft and scale.

### Warnings

* If **velocity > 10 ft/s** in any result → warn:
  “⚠️ Velocity exceeds 10 ft/s; consider upsizing (noise/erosion risk).”
* If **velocity < 3 ft/s** → optional caution:
  “Low velocity may degrade heat transfer/air separation; consider downsizing.”

### Chillers (keep V1 behavior, refine display)

* Show **tons** alongside MW (1 ton ≈ **0.000284 MW**, \~3.517 kW).
* Redundancy models supported: `N+1`, `N+2`, `N+%`.
* Strategy enum already present (Balanced/Modular/Central).
* Respect **max chillers** cap; filter out silly configs (e.g., > 30 units unless strategy demands).
* Keep/format columns: size, count, operating, spare, capacity, loading %, redundancy %, (optional) energy cost if provided.

## Gradio UI (V2)

**Inputs (left column):**

* Layout: `Textbox` (default `2x2x3`)
* Include floors in hall names: `Checkbox` (default OFF)
* Use same MW for all halls: `Checkbox` (default ON)

  * If ON: number input `Default MW per hall` (default `3.0`)
  * If OFF: `Dataframe` with per-hall MW (pre-seeded)
* Fan heat %: `Slider 0–20` (default `0`)
* ΔT (°F): `Number` (default `15`)
* Target velocity (ft/s): `Number` (default `12`)
* Fluid type: `Dropdown` (Water, 30% EG, 50% EG)
* Max ΔP (psi per 100 ft): `Number` (default `20`)
* Shared risers among halls?: `Checkbox` (default ON)
* Riser placement: `Dropdown` (see list)
* Chiller redundancy: `Dropdown` (`N+1`, `N+2`, `N+%`)
* Redundancy % (enabled only if `N+%`): `Slider 10–50` (default `20`)
* Strategy: `Dropdown` (`Balanced`, `Modular`, `Central`)
* Max chillers: `Slider 2–50` (default `20`)
* Electricity rate (\$/kWh): `Number` (default `0.12`)
* **Run Sizing** button

**Outputs (right column):**

* Summary `Markdown`
* Main pipe `Dataframe`
* Per-riser (or per-hall) `Dataframe`
* Top-3 chillers `Dataframe`
* Velocity vs ID `Plot`
* ΔP vs ID `Plot`
* Layout heatmap `Plot`
* Riser stack loads `Plot` (if shared)

## Acceptance Criteria

* Charts render on Render (no “No open ports” errors; plots visible inline).
* Layout parsing validated; bad input shows clean error without crashing.
* With `2x2x3`, same MW = 3.0, fan 5%, ΔT 15°F, Water, vel 12 ft/s:

  * Totals match: per-hall cooling = 3.15 MW; building total = 3.15 × 12 = 37.8 MW.
  * Main pipe \~30" (± one nominal depending on rounding).
  * Shared per-column stacks computed and sized; tables look clean.
  * Plots render with titles/labels, readable in light mode.
* Velocity warnings trigger above 10 ft/s in any segment.
* ΔP reported in psi per 100 ft.

## Deployment

* Ensure `gradio_app.py` launches with:

  ```python
  demo.launch(
    server_name="0.0.0.0",
    server_port=int(os.getenv("PORT", "7860")),
    share=False
  )
  ```
* `requirements.txt` includes:

  ```
  gradio
  pandas
  numpy
  plotly
  matplotlib
  ```

  (Add `kaleido` only if generating PNGs server-side with Plotly.)
* Render (non-Docker):

  * Build: `pip install -r requirements.txt`
  * Start: `python gradio_app.py`
* Optional Dockerfile (pin Python 3.11) if needed.

## Tests

* `parse_layout("2x2x3") == (2,2,3)`; invalid strings raise `ValueError`.
* `make_hall_names(2,2,2,False)` → 4 names; with floors → 8.
* Column aggregates sum to (C×R×F× per-hall MW incl. fan).
* Sizing sanity checks: with 38.4 MW / 15°F / Water / 12 ft/s → main ≈ 30".
* Gradio callback returns figures (not `None`); tables non-empty.

---

