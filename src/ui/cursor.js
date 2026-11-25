import gsap from 'gsap'

export function initCursor() {
  if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) return
  const el = document.querySelector('.cursor')
  const ring = el.querySelector('.cursor__ring')
  const dot = el.querySelector('.cursor__dot')
  const label = el.querySelector('.cursor__label')
  document.documentElement.classList.add('has-cursor')

  const dotX = gsap.quickSetter(dot, 'x', 'px')
  const dotY = gsap.quickSetter(dot, 'y', 'px')
  const ringX = gsap.quickTo(ring, 'x', { duration: 0.55, ease: 'power3.out' })
  const ringY = gsap.quickTo(ring, 'y', { duration: 0.55, ease: 'power3.out' })

  window.addEventListener('pointermove', (e) => {
    dotX(e.clientX)
    dotY(e.clientY)
    ringX(e.clientX)
    ringY(e.clientY)
    el.classList.add('is-visible')
  })
  document.addEventListener('pointerleave', () => el.classList.remove('is-visible'))

  const interactive = 'a, button, [data-cursor-label]'
  document.addEventListener('pointerover', (e) => {
    const target = e.target.closest(interactive)
    el.classList.toggle('is-hover', !!target)
    const text = target?.dataset.cursorLabel || ''
    label.textContent = text
    el.classList.toggle('has-label', !!text)
  })
  document.addEventListener('pointerdown', () => el.classList.add('is-down'))
  document.addEventListener('pointerup', () => el.classList.remove('is-down'))
}
