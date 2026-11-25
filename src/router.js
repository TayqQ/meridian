// Minimal client-side router: fetch the next page, swap <main> under a curtain,
// keep the WebGL canvas alive so the watch carries across pages. Same-page
// jumps (nav anchors, logo) also go under the curtain: scrolling there would
// replay every scroll-driven pose on the way at high speed.
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

const normalize = (path) => path.replace(/\/index\.html$/, '/')

// A pinned section gets moved within its pin-spacer once scrolled past, so the
// spacer is what marks where the section really starts.
const anchorFor = (hash) => {
  const el = hash ? document.querySelector(hash) : null
  return el?.closest('.pin-spacer') ?? el
}
const topOf = (el) => (el ? el.getBoundingClientRect().top + window.scrollY : 0)

// Jump straight to a scroll position and finish every scrubbed animation, so
// the watch is already in its final pose there rather than catching up.
export function jumpTo(app, target) {
  const el = typeof target === 'string' ? anchorFor(target) : null
  if (typeof target === 'string' && !el) return
  const top = el ? topOf(el) : target
  if (app.lenis) {
    app.lenis.resize() // the page may have just been swapped or pinned; refresh the scroll limit first
    app.lenis.scrollTo(top, { immediate: true, force: true })
  } else window.scrollTo(0, top)
  ScrollTrigger.update()

  // Several scrubbed animations write to the same watch pose. Settle them in an
  // order where the section we landed in writes last: first everything further
  // down the page, then everything already reached, top to bottom.
  const y = window.scrollY
  const settle = (st) => {
    const scrub = st.getTween() // false unless scrub is a smoothing duration
    if (scrub) scrub.progress(1)
    const a = st.animation
    if (!a) return
    // Sweep in from the far end so every child of a timeline (labels, step
    // text) passes through and lands in its correct state, then render the
    // target with force: an earlier settle may have overwritten what this
    // animation last wrote, and an unchanged time would otherwise be skipped.
    a.render(st.progress > 0.5 ? 0 : a.totalDuration(), true, true)
    a.render(a.totalDuration() * st.progress, true, true)
  }
  const all = ScrollTrigger.getAll()
  all.filter((st) => st.start > y).forEach(settle)
  all.filter((st) => st.start <= y).sort((a, b) => a.start - b.start).forEach(settle)
}

export function createRouter(app, mount) {
  const curtain = document.querySelector('.curtain')
  let busy = false
  history.scrollRestoration = 'manual'

  const cover = () =>
    gsap.fromTo(
      curtain,
      { clipPath: 'inset(100% 0% 0% 0%)', visibility: 'visible' },
      { clipPath: 'inset(0% 0% 0% 0%)', duration: 0.9, ease: 'expo.inOut' },
    )
  const reveal = () => gsap.to(curtain, { clipPath: 'inset(0% 0% 100% 0%)', duration: 1.1, ease: 'expo.inOut', delay: 0.1 })

  function markCurrent() {
    document.querySelectorAll('.nav a').forEach((a) => {
      const url = new URL(a.href)
      const active = !url.hash && normalize(url.pathname) === normalize(location.pathname)
      a.toggleAttribute('aria-current', active)
    })
  }

  async function navigate(url, push) {
    if (busy) return
    busy = true
    const html = fetch(url.pathname).then((r) => r.text())
    app.lenis?.stop()

    gsap.to(app.stage.state, { intro: 0.3, duration: 0.9, ease: 'power3.in' })
    await cover()

    const doc = new DOMParser().parseFromString(await html, 'text/html')
    if (push) history.pushState({}, '', url)
    document.title = doc.title
    const page = mount(doc.querySelector('main'))
    markCurrent()
    if (url.hash) jumpTo(app, url.hash)

    reveal()
    gsap.delayedCall(0.35, () => page.enter())
    app.lenis?.start()
    busy = false
  }

  async function jump(hash) {
    if (Math.abs(topOf(anchorFor(hash)) - window.scrollY) < 4 || busy) return
    if (app.reduced) return jumpTo(app, hash || 0)
    busy = true
    app.lenis?.stop()
    await cover()
    try {
      jumpTo(app, hash || 0)
    } finally {
      reveal()
      app.lenis?.start()
      busy = false
    }
  }

  document.addEventListener('click', (e) => {
    const a = e.target.closest('a')
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || a.target === '_blank' || a.hasAttribute('download')) return
    const url = new URL(a.href, location.href)
    if (url.origin !== location.origin) return
    e.preventDefault()
    if (normalize(url.pathname) === normalize(location.pathname)) {
      if (url.hash !== location.hash) history.replaceState({}, '', url)
      jump(url.hash)
      return
    }
    navigate(url, true)
  })

  window.addEventListener('popstate', () => navigate(new URL(location.href), false))
  markCurrent()
}
