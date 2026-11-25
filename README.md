# Meridian — Calibre 01

A mock award-style product launch site for a fictional mechanical watch. Built as a test of how far Claude Code can take an Awwwards-tier site from a couple of prompts: the scroll story, the WebGL scene and the watch model itself (a scripted Blender build) were all generated with it.

Not a real brand or product.

## Stack

Vite, Three.js, GSAP (ScrollTrigger, SplitText) and Lenis. One WebGL canvas persists across pages through a small History-API router.

## Run it

```bash
npm install
npm run dev
```

| Command | What it does |
|---|---|
| `npm run dev` | Dev server |
| `npm run build` | Production build into `dist/` |
| `npm run model` | Rebuild `public/models/watch.glb` from `blender/build_watch.py` (needs Blender) |

`PLAN.md` has the original brief, the design notes and an honest status section.
