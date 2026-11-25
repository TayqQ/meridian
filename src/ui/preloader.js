import gsap from 'gsap'

// Counts towards real load progress, finishes once `ready` resolves (and a
// minimum beat has passed), then resolves as the curtain starts lifting so the
// page intro overlaps the reveal.
export function runPreloader({ reduced }, ready, progress = () => 1) {
  const el = document.querySelector('.preloader')
  const count = el.querySelector('.preloader__count')
  const bar = el.querySelector('.preloader__bar span')
  const shown = { v: 0 }
  const render = () => {
    count.textContent = String(Math.round(shown.v)).padStart(3, '0')
    bar.style.transform = `scaleX(${shown.v / 100})`
  }
  const creep = () => {
    shown.v += (Math.min(90, 8 + progress() * 82) - shown.v) * 0.06
    render()
  }
  gsap.ticker.add(creep)
  const minimum = new Promise((r) => setTimeout(r, reduced ? 200 : 1600))

  return Promise.all([ready, minimum]).then(
    () =>
      new Promise((resolve) => {
        gsap.ticker.remove(creep)
        gsap
          .timeline({ onComplete: () => el.remove() })
          .to(shown, { v: 100, duration: reduced ? 0.1 : 0.6, ease: 'power2.inOut', onUpdate: render })
          .to(el.querySelectorAll('.preloader__count, .preloader__name'), { yPercent: -110, duration: 0.6, ease: 'power3.in', stagger: 0.05 })
          .call(resolve)
          .to(el, { clipPath: 'inset(0% 0% 100% 0%)', duration: 1.2, ease: 'expo.inOut' }, '<')
      }),
  )
}
