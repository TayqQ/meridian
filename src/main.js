import 'lenis/dist/lenis.css'
import './style.css'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { SplitText } from 'gsap/SplitText'
import Lenis from 'lenis'
import { createStage } from './scene/stage.js'
import { initCursor } from './ui/cursor.js'
import { runPreloader } from './ui/preloader.js'
import { createRouter, jumpTo } from './router.js'
import { magnetic } from './pages/shared.js'
import home from './pages/home.js'
import craft from './pages/craft.js'

gsap.registerPlugin(ScrollTrigger, SplitText)

const pages = { home, craft }
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

let lenis = null
if (!reduced) {
  lenis = new Lenis({ lerp: 0.085, wheelMultiplier: 0.9 })
  lenis.on('scroll', ScrollTrigger.update)
  gsap.ticker.add((time) => lenis.raf(time * 1000))
  gsap.ticker.lagSmoothing(0)
}

const stage = createStage(document.querySelector('.webgl'), { reduced })
const app = { lenis, stage, reduced }
let current = null
if (import.meta.env.DEV) Object.assign(window, { __meridian: app, __ST: ScrollTrigger }) // console debugging only

// Tear down the old page, swap in the new <main>, build its timelines.
function mount(nextMain) {
  current?.destroy()
  const main = document.querySelector('main')
  if (nextMain !== main) main.replaceWith(nextMain)
  window.scrollTo(0, 0)
  lenis?.scrollTo(0, { immediate: true, force: true })
  current = pages[nextMain.dataset.page](nextMain, app)
  gsap.set(stage.state, { ...current.initialPose, intro: 0 })
  ScrollTrigger.refresh()
  return current
}

initCursor()
document.querySelectorAll('.nav [data-magnetic]').forEach((el) => magnetic(el))

// The preloader counts real model download progress, then lifts once the
// watch and fonts are ready and the first page is mounted underneath.
let progress = 0
const mounted = Promise.all([stage.load((p) => (progress = p)), document.fonts.ready]).then(() => {
  const page = mount(document.querySelector('main'))
  if (location.hash) jumpTo(app, location.hash) // land on the section while still covered
  return page
})
await runPreloader(app, mounted, () => progress)
const first = await mounted
first.enter()
createRouter(app, mount)
