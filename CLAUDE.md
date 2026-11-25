# Meridian (Calibre 01)

A mock award-style product launch site for a fictional watch, built to test how far Claude Code can take an Awwwards-tier site. Portfolio piece, not a client job. `PLAN.md` is the brief, status and pipeline: read §7 (status) and §8 (the Blender model) at the start of a session, and the rest only when needed.

## Stack

Vite 8 (no framework), Three.js, GSAP 3 (ScrollTrigger, SplitText), Lenis. npm, not pnpm. Git repo `TayqQ/meridian` (public); commits use the GitHub noreply email set in the local git config. Pushing `main` deploys to production on Vercel: https://meridian-mu-brown.vercel.app

## Layout

- `index.html` (home) and `craft.html` (craft page) are both Vite inputs (`vite.config.js`).
- `src/main.js` boots the app; `src/router.js` is the History-API router that keeps one WebGL canvas across pages.
- `src/scene/stage.js` (renderer, camera, lights, environment) and `src/scene/watch.js` (loads the GLB, matches materials by name, poses).
- `src/pages/home.js`, `craft.js`, `shared.js`: the scroll timelines. `src/ui/`: preloader and cursor.
- `blender/build_watch.py` builds the model; `blender/build.sh` exports, compresses (meshopt) and converts textures into `public/models/`.

## Commands

| Command | What it does |
|---|---|
| `npm run dev` | Dev server. The preview config `meridian` in `../.claude/launch.json` attaches to it on port 5174. |
| `npm run build` | Production build into `dist/`. Preview config `meridian-prod` serves it on port 4174. |
| `npm run model` | Rebuild `public/models/watch.glb` from the Blender script (headless Blender from `/Applications`, or set `BLENDER`) |
| `npm run model -- --render` | Same, plus Cycles reference stills in `blender/renders/` |

## Rules

- Change the model through `build_watch.py` and `npm run model`, never by hand-editing the GLB or the `.blend`. Part and material names are what `watch.js` and the timelines look up: rename them in both places at once.
- Check visual changes in the browser at 1440×900 and 375×812 before calling them done, and say what you couldn't check (Safari, real phones, frame rate).
- Performance budget (PLAN.md §6): under 3 MB first load, 60 fps on an M1, 30 fps on a mid-range phone.
- When a session ends, update PLAN.md §7 (what works, honest gaps) so the next session starts from it.
