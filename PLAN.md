# MERIDIAN — Calibre 01
### A mock "Awwwards-tier" product launch site, built with Claude Code

---

## 1. Can Claude Code do this, and who does what?

The work behind an Awwwards site splits into five disciplines. Claude Code is strong at some of them and weak at others.

| Discipline | What it involves | Claude Code | Skilled human |
|---|---|---|---|
| **Creative direction** | Concept, story, art direction, the one idea that makes people remember the site | Can suggest concepts and reference trends. Its taste is competent but generic. | **Owns this.** This is most of what a 5-figure fee pays for. |
| **Visual / UI design** | Type, grid, colour, composition, motion language (usually in Figma) | Can design straight in code to a decent standard and can read Figma via MCP. | **Owns this.** Pixel-level taste, rhythm and restraint. |
| **3D assets** | Modelling, UVs, PBR texturing, baking, rigging, export to GLB | Can write Blender Python scripts, build procedural geometry, and optimise GLBs (gltf-transform, Draco, KTX2). It can't sculpt or judge a model by eye very well. | **Owns hero assets.** A good product model takes a 3D artist days. |
| **Front-end engineering** | Three.js scenes, shaders, GSAP timelines, scroll orchestration, routing, transitions, responsive work, performance | **Very strong, around 70–85% of the work.** Boilerplate, shaders, timelines, routers, loaders and responsive layouts come out fast and correct. | Steers, reviews, and tunes the *feel*. |
| **Motion polish & QA** | Easing curves, timing, "juice", cross-device testing, frame-rate tuning | Can do a first pass and check in a browser, but it can't *feel* 60fps or judge whether an easing curve is satisfying. | **Owns the final 10–20%.** This is what separates "nice" from "SOTD". |

**Bottom line:** Claude Code takes on most of the *engineering* load, which is often 50–60% of an agency's hours. That turns a 6–10 week build into something a designer-developer pair can ship in 1–3 weeks. It doesn't replace the art director, the 3D artist, or the person with the taste to cut 80% of the ideas. The best setup is **a human with taste directing Claude Code**, iterating in tight loops: "the ease is too linear", "hold the camera 300ms longer", "the gold reads as yellow plastic".

---

## 2. Inspiration (current Awwwards Sites of the Day, Oct 2026)

| Site | What to borrow |
|---|---|
| **Forge Automotive** (GSAP, WebGL, Next.js) | Luxury tone, parallax, scroll storytelling, infinite scroll, transitions |
| **Cartier: Le Chœur des Pierres** (WebGL) | Product-as-hero, slow cinematic reveals, restrained luxury palette |
| **Pegassi: Ascension** (Three.js, GSAP, Nuxt) | 3D + sound + micro-interactions working together |
| **Riotters: LiDAR Drone** (Three.js, Next.js) | Technical/engineering storytelling, gesture interaction |
| **Overworld Audio** (Three.js, Nuxt, Sanity) | Immersive 3D world with sound design |

The **stack these winners share**: Three.js/WebGL + GSAP (ScrollTrigger) + smooth scroll + a framework router with a persistent canvas.

---

## 3. The mock brief

**MERIDIAN** is a fictional independent watchmaker launching its first mechanical watch, **Calibre 01**.
**Tone:** quiet luxury, engineering precision. Black, bone and brushed gold.
**Hero idea:** *The watch comes apart.* As you scroll, the watch rotates and explodes into its components (crystal, bezel, dial, hands, movement, gears, caseback), then reassembles for the purchase moment.

### User journey
1. **Preloader.** A counter runs from 000 to 100 while the 3D scene builds, then a curtain lifts.
2. **Hero.** A giant split-text headline staggers in. The watch floats, catches the light, and tilts toward the cursor.
3. **"Engineered in layers".** The section pins and scroll drives the exploded view. Callout labels fade in by each part.
4. **Materials.** You pick a finish (Gold / Steel / Black). The 3D materials tween live and the background colour shifts.
5. **Specs.** A pinned horizontal scroll of spec cards, with counters that tick up.
6. **Marquee + CTA.** An infinite velocity-reactive marquee and a magnetic "Reserve" button. The watch reassembles.
7. **Page transition** to **/craft**. A curtain wipes across while the persistent WebGL camera moves to a new composition, then the new page's text reveals.

### Effects inventory
- [x] Persistent Three.js canvas across routes (PBR metals, RoomEnvironment reflections, soft shadows)
- [x] Scroll-scrubbed exploded view (GSAP ScrollTrigger timeline driving 3D transforms)
- [x] Cursor-reactive tilt plus idle float
- [x] Live material/colour swap
- [x] Lenis smooth scroll synced to the GSAP ticker
- [x] Split-text line/char reveals (GSAP SplitText, free since 3.13)
- [x] Custom cursor with hover states, magnetic buttons
- [x] Preloader with counter, curtain page transitions, client-side router (History API)
- [x] Pinned horizontal scroll section, number counters
- [x] Velocity-reactive marquee
- [x] Film grain overlay, `prefers-reduced-motion` fallback
- [ ] *Phase 2:* WebGL image hover distortion (custom shader), sound design, post-processing (bloom/DOF), Blender GLB

---

## 4. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Build | **Vite** | Instant HMR. Framework-free keeps the demo transparent. |
| 3D | **Three.js** | Industry standard |
| Animation | **GSAP 3** + ScrollTrigger + SplitText | Industry standard for award sites. 100% free since 2025. |
| Scroll | **Lenis** | Smooth, inertial scroll that sits well with ScrollTrigger |
| Routing | Custom History-API router (~60 lines) | Shows how persistent-canvas transitions work. Swap for Barba.js, Astro view transitions or Next/Nuxt in production. |
| Production | Next.js/Nuxt + headless CMS (Sanity) | What the reference sites use |

---

## 5. The Blender → web pipeline (for the real version)

The v1 prototype builds the watch **procedurally in code** (Blender isn't installed on this machine), so every part is a named mesh we can animate. The production pipeline is:

1. **Model in Blender** with each animatable part as a separate, sensibly named object (`crystal`, `bezel`, `dial`, `hand_hour`, `gear_01`…), origins at their pivots.
2. **Bake** AO and lighting into textures where possible (cheap realism). Keep metals as true PBR.
3. **Export glTF 2.0 (.glb)**, then optimise: `npx @gltf-transform/cli optimize in.glb out.glb --compress draco --texture-compress ktx2`.
4. **In code**, swap `buildWatch()` for `GLTFLoader` and look parts up by name. The scroll timelines don't change.
5. Claude Code can *script* steps 1–3 with Blender's Python API (`blender -b -P script.py`) for procedural or parametric objects. Hero-grade modelling is still a 3D artist's job.

---

## 6. Phases

| Phase | Scope | Who leads |
|---|---|---|
| **0. Concept** | Brief, references, moodboard, journey | Human (Claude assists) |
| **1. Prototype (this repo)** | Full journey, all core effects, procedural model | **Claude Code** |
| **2. Design pass** | Figma art direction, then Claude implements it | Human designer → Claude |
| **3. Asset pass** | Blender model, textures, GLB optimisation | 3D artist → Claude integrates |
| **4. Motion polish** | Easing, timing, sound, shaders, post FX | Human + Claude in tight loops |
| **5. Hardening** | Mobile fallbacks, perf budget (<3 MB first load, 60fps on an M1, 30fps on a mid-range phone), a11y, SEO, CMS | Claude Code (human QA) |

## 7. v1 status (built and checked in-browser at 1440×900 and 375×812)

**Working:** preloader → hero split-text intro; pinned exploded view with projected 3D callouts and a step counter; live finish swap (metal, dial, accent, background, price); pinned horizontal spec cards with glass blur and count-ups; velocity-reactive marquee; magnetic CTA; curtain page transition to `/craft.html` with the same WebGL watch carried across and re-posed per chapter; custom cursor; film grain; mobile poses.

**Not done / honest gaps:**
- The watch is procedural. It reads as "good product render", not "photoreal hero asset". A Blender model with baked textures is the single biggest quality jump.
- No sound design, post-processing (bloom/DOF), or custom shaders yet.
- Only tested in Chromium. Not yet tested in Safari or Firefox, on real phones, or against a frame-rate budget.
- The motion timings are a first pass and need a human "feel" pass.
- JS bundle is ~206 KB gzipped (mostly Three.js). Fine for now; would code-split in production.

## 8. The Blender model (done)

`npm run model` rebuilds the watch from [blender/build_watch.py](blender/build_watch.py):

- **Model.** About 60 named parts: a lathed case with bulged flanks, swept lugs, a knurled crown, a 72-flute bezel, a domed sapphire, a sunburst dial with Didot printing as raised geometry, faceted applied indices and dauphine hands. The movement has a perlage plate, Côtes de Genève bridges with chamfered edges, gold wheels, jewels in chatons, blued screws, a balance with timing screws and hairspring, and a rotor with a gold weight. The bracelet is three-piece links with polished chamfers.
- **Textures.** The finishing normal maps (Côtes de Genève, perlage) are generated procedurally with numpy.
- **Export and compression.** The GLB is exported, then compressed with meshopt: 5.9 MB → 1.1 MB. The textures ship as 1024px JPEGs.
- **Reference renders.** `npm run model -- --render` adds Cycles reference stills in `blender/renders/`.
- **In the browser.** Materials are matched by name and replaced with tuned `MeshPhysicalMaterial`s: a radial anisotropy map for the sunburst dial, iridescence for the blued screws, and anisotropic brushing on the bracelet. Reflections come from a procedural studio-softbox environment.

## 9. Run it
```
npm install
npm run dev
```
