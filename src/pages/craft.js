import gsap from 'gsap'
import { makePoses, poseScrub, setupReveals, countUp, magnetic, heroIntro } from './shared.js'

const pose = makePoses(
  {
    hero: { vx: 0.26, vy: 0, scale: 0.86, rotX: 0.25, rotY: 2.75, rotZ: 0.25, explode: 0.2, idle: 1 },
    c1: { vx: 0.26, vy: 0, scale: 0.8, rotX: 0.4, rotY: 3.5, rotZ: -0.1, explode: 0.55, idle: 0.3 },
    c2: { vx: -0.26, vy: 0, scale: 0.78, rotX: 0.5, rotY: 2.6, rotZ: 0.3, explode: 0.9, idle: 0.3 },
    c3: { vx: 0.26, vy: 0, scale: 0.8, rotX: 0.3, rotY: 3.9, rotZ: -0.2, explode: 0.35, idle: 0.3 },
    c4: { vx: -0.26, vy: 0, scale: 0.82, rotX: 0.12, rotY: 6.0, rotZ: 0.05, explode: 0, idle: 1 },
    next: { vx: 0, vy: 0.14, scale: 0.55, rotX: 0.1, rotY: 6.28, rotZ: 0, explode: 0, idle: 1 },
  },
  {
    hero: { vx: 0, vy: 0.22, scale: 0.8 },
    c1: { vx: 0, vy: 0.26, scale: 0.7 },
    c2: { vx: 0, vy: 0.26, scale: 0.7 },
    c3: { vx: 0, vy: 0.26, scale: 0.7 },
    c4: { vx: 0, vy: 0.26, scale: 0.7 },
    next: { vx: 0, vy: 0.3, scale: 0.6 },
  },
)

export default function craft(main, app) {
  const { state } = app.stage
  const disposers = []

  const ctx = gsap.context(() => {
    setupReveals(main)

    gsap.to('.craft-hero__inner', {
      yPercent: -20,
      autoAlpha: 0,
      ease: 'none',
      scrollTrigger: { trigger: '.craft-hero', start: 'top top', end: 'bottom top', scrub: true },
    })

    // Each section hands the watch to the next pose as it scrolls in
    const order = ['hero', 'c1', 'c2', 'c3', 'c4', 'next']
    main.querySelectorAll('[data-pose]').forEach((section) => {
      const to = section.dataset.pose
      const from = order[order.indexOf(to) - 1]
      poseScrub(state, pose, from, to, { trigger: section, start: 'top bottom', end: 'top top' })
    })

    main.querySelectorAll('.chapter__num').forEach((el) => {
      gsap.fromTo(el, { yPercent: 30 }, { yPercent: -30, ease: 'none', scrollTrigger: { trigger: el.closest('.chapter'), scrub: true } })
    })
    main.querySelectorAll('[data-count]').forEach((el) => countUp(el, { trigger: el, start: 'top 85%' }))
    main.querySelectorAll('[data-magnetic]').forEach((el) => disposers.push(magnetic(el)))
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
