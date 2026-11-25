import gsap from 'gsap'
import { SplitText } from 'gsap/SplitText'

export const KEYS = ['vx', 'vy', 'scale', 'rotX', 'rotY', 'rotZ', 'explode', 'idle']
export const isMobile = () => window.innerWidth < 768

// A page's poses: desktop values with optional mobile overrides.
export function makePoses(desktop, mobile = {}) {
  return (name) => (isMobile() ? { ...desktop[name], ...mobile[name] } : desktop[name])
}

// Function-based values re-evaluate on ScrollTrigger refresh, so poses follow breakpoints.
export function vals(pose, name) {
  return Object.fromEntries(KEYS.map((k) => [k, () => pose(name)[k]]))
}

// Scrubbed pose-to-pose tween. Ranges are laid out back to back so the `to`
// of one section is always the `from` of the next, which keeps reverse scrolling seamless.
export function poseScrub(state, pose, from, to, scrollTrigger) {
  return gsap.fromTo(state, vals(pose, from), {
    ...vals(pose, to),
    ease: 'none',
    immediateRender: false,
    scrollTrigger: { scrub: 0.8, invalidateOnRefresh: true, ...scrollTrigger },
  })
}

export function setupReveals(scope) {
  scope.querySelectorAll('[data-split]').forEach((el) => {
    SplitText.create(el, {
      type: 'lines',
      mask: 'lines',
      autoSplit: true,
      onSplit: (self) =>
        gsap.from(self.lines, {
          yPercent: 110,
          duration: 1.2,
          ease: 'expo.out',
          stagger: 0.09,
          scrollTrigger: { trigger: el, start: 'top 85%', once: true },
        }),
    })
  })
  scope.querySelectorAll('[data-reveal]').forEach((el) => {
    gsap.from(el, {
      y: 28,
      autoAlpha: 0,
      duration: 1.1,
      ease: 'power3.out',
      scrollTrigger: { trigger: el, start: 'top 88%', once: true },
    })
  })
}

export function countUp(el, scrollTrigger) {
  const target = parseFloat(el.dataset.count)
  const decimals = Number(el.dataset.decimals || 0)
  const fmt = new Intl.NumberFormat('en-GB', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  const obj = { v: 0 }
  el.textContent = fmt.format(0)
  return gsap.to(obj, {
    v: target,
    duration: 2,
    ease: 'expo.out',
    onUpdate: () => (el.textContent = fmt.format(obj.v)),
    scrollTrigger: { once: true, ...scrollTrigger },
  })
}

export function magnetic(el, strength = 0.35) {
  if (!window.matchMedia('(hover: hover)').matches) return () => {}
  const xTo = gsap.quickTo(el, 'x', { duration: 0.6, ease: 'power3.out' })
  const yTo = gsap.quickTo(el, 'y', { duration: 0.6, ease: 'power3.out' })
  const move = (e) => {
    const r = el.getBoundingClientRect()
    xTo((e.clientX - (r.left + r.width / 2)) * strength)
    yTo((e.clientY - (r.top + r.height / 2)) * strength)
  }
  const leave = () => {
    gsap.to(el, { x: 0, y: 0, duration: 1, ease: 'elastic.out(1, 0.35)', overwrite: true })
  }
  el.addEventListener('pointermove', move)
  el.addEventListener('pointerleave', leave)
  return () => {
    el.removeEventListener('pointermove', move)
    el.removeEventListener('pointerleave', leave)
  }
}

// Hero headline intro shared by every page.
export function heroIntro(main, state) {
  const title = main.querySelector('[data-hero-title]')
  const split = SplitText.create(title, { type: 'lines,chars', mask: 'lines' })
  gsap.set(title, { visibility: 'visible' })
  return gsap
    .timeline()
    .fromTo(state, { intro: 0 }, { intro: 1, duration: 2.4, ease: 'expo.out' }, 0)
    .from(split.chars, { yPercent: 120, duration: 1.3, ease: 'expo.out', stagger: 0.025 }, 0.1)
    .from(main.querySelectorAll('[data-fade]'), { autoAlpha: 0, y: 16, duration: 1, stagger: 0.08, ease: 'power3.out' }, 0.5)
}
