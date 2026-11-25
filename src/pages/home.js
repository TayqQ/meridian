import gsap from 'gsap'
import { FINISHES } from '../scene/watch.js'
import { makePoses, vals, poseScrub, setupReveals, countUp, magnetic, heroIntro } from './shared.js'

const pose = makePoses(
  {
    hero: { vx: 0.27, vy: 0, scale: 0.8, rotX: 0.14, rotY: -0.42, rotZ: 0.1, explode: 0, idle: 1 },
    layers: { vx: 0.04, vy: 0, scale: 0.74, rotX: 0.3, rotY: -0.95, rotZ: 0, explode: 0, idle: 0 },
    exploded: { vx: 0.04, vy: -0.03, scale: 0.6, rotX: 0.34, rotY: -1.05, rotZ: -0.06, explode: 1, idle: 0 },
    material: { vx: -0.25, vy: 0, scale: 0.62, rotX: 0.1, rotY: 0.22, rotZ: -0.06, explode: 0, idle: 1 },
    specs: { vx: 0, vy: 0, scale: 0.78, rotX: 0.3, rotY: 3.3, rotZ: 0.2, explode: 0.12, idle: 0 },
    specsEnd: { vx: 0, vy: 0, scale: 0.78, rotX: 0.3, rotY: 3.3, rotZ: 1.0, explode: 0.5, idle: 0 },
    cta: { vx: 0.25, vy: 0, scale: 0.78, rotX: 0.1, rotY: 6.0, rotZ: 0.05, explode: 0, idle: 1 },
  },
  {
    hero: { vx: 0, vy: 0.2, scale: 0.85 },
    layers: { vx: 0, vy: 0.05, rotX: 0.9, rotY: -0.3 },
    exploded: { vx: 0, vy: 0.08, rotX: 1.05, rotY: -0.35, scale: 0.6 },
    material: { vx: 0, vy: 0.4, scale: 0.5 },
    specs: { scale: 0.8 },
    specsEnd: { scale: 0.8 },
    cta: { vx: 0, vy: 0.4, scale: 0.55 },
  },
)

export default function home(main, app) {
  const { stage, lenis } = app
  const { state } = stage
  const disposers = []
  const q = (s) => main.querySelector(s)
  const qa = (s) => [...main.querySelectorAll(s)]

  const ctx = gsap.context(() => {
    setupReveals(main)

    // Hero -> anatomy
    gsap.to('.hero__inner', {
      yPercent: -20,
      autoAlpha: 0,
      ease: 'none',
      scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true },
    })
    poseScrub(state, pose, 'hero', 'layers', { trigger: '.hero', start: 'top top', end: 'bottom top' })

    // Anatomy: pinned, scroll drives the exploded view and the callouts
    const labels = qa('.label')
    const steps = qa('.step')
    const num = q('.layers__num')
    const STEP = 0.75
    const FIRST = 0.9
    const tl = gsap.timeline({
      defaults: { ease: 'none' },
      // counter follows the (smoothed) timeline itself, so it agrees with the step text
      onUpdate: () => {
        const i = gsap.utils.clamp(0, steps.length - 1, Math.floor((tl.time() - FIRST) / STEP))
        num.textContent = String(i + 1).padStart(2, '0')
      },
      scrollTrigger: {
        trigger: '.layers',
        start: 'top top',
        end: '+=360%',
        pin: true,
        scrub: 1,
        invalidateOnRefresh: true,
      },
    })
    tl.fromTo(state, vals(pose, 'layers'), { ...vals(pose, 'exploded'), duration: 6, immediateRender: false }, 0.001)
    labels.forEach((label, i) => tl.fromTo(label, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.35 }, FIRST + i * STEP))
    steps.forEach((step, i) => {
      const at = FIRST + i * STEP
      tl.fromTo(step, { autoAlpha: 0, y: 24 }, { autoAlpha: 1, y: 0, duration: 0.3 }, at)
      if (i < steps.length - 1) tl.to(step, { autoAlpha: 0, y: -24, duration: 0.3 }, at + STEP - 0.1)
    })
    tl.to(labels, { autoAlpha: 0, duration: 0.4 }, 6.1).to({}, { duration: 0.3 })

    // Callouts track their 3D part every frame
    disposers.push(
      stage.onFrame(() => {
        for (const label of labels) {
          if (label.style.visibility === 'hidden') continue
          const p = stage.project(stage.anchors[label.dataset.part])
          label.style.transform = `translate3d(${p.x}px, ${p.y}px, 0)`
        }
      }),
    )

    // Finish
    poseScrub(state, pose, 'exploded', 'material', { trigger: '.materials', start: 'top bottom', end: 'top top' })
    const price = q('[data-price]')
    qa('.swatch').forEach((btn) => {
      const onClick = () => {
        const fin = FINISHES[btn.dataset.finish]
        qa('.swatch').forEach((b) => {
          b.classList.toggle('is-active', b === btn)
          b.setAttribute('aria-checked', String(b === btn))
        })
        stage.setFinish(btn.dataset.finish)
        gsap.to(document.documentElement, { '--bg': fin.bg, '--accent': fin.accent, duration: 1.2, ease: 'power2.inOut' })
        gsap
          .timeline()
          .to(price, { yPercent: -100, autoAlpha: 0, duration: 0.35, ease: 'power3.in' })
          .call(() => (price.textContent = fin.price))
          .fromTo(price, { yPercent: 100, autoAlpha: 0 }, { yPercent: 0, autoAlpha: 1, duration: 0.6, ease: 'expo.out' })
      }
      btn.addEventListener('click', onClick)
      disposers.push(() => btn.removeEventListener('click', onClick))
    })

    // Specs: pinned horizontal track, watch turns to show the movement
    poseScrub(state, pose, 'material', 'specs', { trigger: '.specs', start: 'top bottom', end: 'top top' })
    const track = q('.specs__track')
    const distance = () => track.scrollWidth - window.innerWidth
    const horizontal = gsap.to(track, {
      x: () => -distance(),
      ease: 'none',
      scrollTrigger: { trigger: '.specs', start: 'top top', end: () => `+=${distance()}`, pin: true, scrub: 1, invalidateOnRefresh: true },
    })
    poseScrub(state, pose, 'specs', 'specsEnd', { trigger: '.specs', start: 'top top', end: () => `+=${distance()}` })
    qa('[data-count]').forEach((el) =>
      countUp(el, { trigger: el.closest('.spec'), containerAnimation: horizontal, start: 'left 85%' }),
    )

    // Marquee: speed and direction follow scroll velocity
    const marquee = gsap.to('.marquee__track', { xPercent: -50, duration: 22, ease: 'none', repeat: -1 })
    if (lenis) {
      const onScroll = ({ velocity, direction }) => {
        const dir = direction < 0 ? -1 : 1
        gsap.to(marquee, { timeScale: dir * (1 + Math.min(Math.abs(velocity) * 0.25, 6)), duration: 0.25, overwrite: true })
        gsap.to(marquee, { timeScale: dir, duration: 1.2, delay: 0.25 })
      }
      lenis.on('scroll', onScroll)
      disposers.push(() => lenis.off('scroll', onScroll))
    }

    // Reserve
    poseScrub(state, pose, 'specsEnd', 'cta', { trigger: '.marquee', start: 'top bottom', endTrigger: '.cta', end: 'center center' })
    const reserve = q('.btn-reserve')
    const onReserve = () => {
      if (reserve.classList.contains('is-done')) return
      reserve.classList.add('is-done')
      const label = reserve.querySelector('.btn__label')
      gsap
        .timeline()
        .to(label, { yPercent: -120, duration: 0.35, ease: 'power3.in' })
        .call(() => (label.textContent = 'You’re on the list'))
        .fromTo(label, { yPercent: 120 }, { yPercent: 0, duration: 0.6, ease: 'expo.out' })
    }
    reserve.addEventListener('click', onReserve)
    disposers.push(() => reserve.removeEventListener('click', onReserve))

    qa('[data-magnetic]').forEach((el) => disposers.push(magnetic(el)))
  }, main)

  return {
    initialPose: pose('hero'),
    enter() {
      let intro
      ctx.add(() => (intro = heroIntro(main, state)))
      return intro
    },
    destroy() {
      disposers.forEach((d) => d())
      ctx.revert()
    },
  }
}
