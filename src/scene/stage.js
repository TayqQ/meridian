// One persistent WebGL stage shared by every page. Pages never touch Three.js
// directly; they tween `state`, and the render loop turns it into transforms.
import * as THREE from 'three'
import gsap from 'gsap'
import { loadWatch } from './watch.js'

// A photo studio for reflections. Polished metal is mostly reflections, so
// this decides how the watch reads. A mid-grey room means every facet reflects
// something (no dead-black patches). Softboxes surround the watch on all sides,
// including behind and below, because it turns through every angle. All light
// is neutral white and kept moderate, so highlights never wash out the metal's
// own colour.
function studioEnvironment(renderer) {
  const env = new THREE.Scene()
  env.add(new THREE.Mesh(new THREE.SphereGeometry(30, 32, 16), new THREE.MeshBasicMaterial({ color: '#4a4a4a', side: THREE.BackSide })))
  const panel = (w, h, intensity, pos) => {
    const m = new THREE.Mesh(
      new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 1, 1).multiplyScalar(intensity), side: THREE.DoubleSide }),
    )
    m.position.set(...pos)
    m.lookAt(0, 0, 0)
    env.add(m)
  }
  panel(14, 10, 1.8, [0, 6, 12]) // front key
  panel(12, 16, 1.4, [-13, 2, 4]) // left
  panel(12, 16, 1.4, [13, 2, 4]) // right
  panel(12, 12, 1.2, [-9, 3, -10]) // back left
  panel(12, 12, 1.2, [9, 3, -10]) // back right
  panel(20, 20, 1.4, [0, 14, 0]) // overhead
  panel(18, 18, 0.7, [0, -14, 0]) // floor bounce
  panel(1.2, 18, 2.2, [-11, 0, -1]) // narrow strips: crisp edge definition
  panel(1.2, 18, 2.0, [11, 0, 1])
  const pmrem = new THREE.PMREMGenerator(renderer)
  const tex = pmrem.fromScene(env, 0.035).texture
  pmrem.dispose()
  return tex
}

export function createStage(canvas, { reduced = false } = {}) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.toneMapping = THREE.NeutralToneMapping // keeps gold saturated where AgX greys it out
  renderer.toneMappingExposure = 1.0

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(28, 1, 0.1, 100)
  camera.position.set(0, 0, 10)

  scene.environment = studioEnvironment(renderer)

  const key = new THREE.DirectionalLight('#ffffff', 0.8)
  key.position.set(4, 5, 6)
  scene.add(key)

  const rig = new THREE.Group()
  const tilt = new THREE.Group()
  rig.add(tilt)
  scene.add(rig)
  let watch = null

  // vx/vy are fractions of the half-viewport, so poses survive any aspect ratio.
  const state = { vx: 0, vy: 0, scale: 1, rotX: 0, rotY: 0, rotZ: 0, explode: 0, idle: 0, intro: 0 }

  const pointer = { x: 0, y: 0, tx: 0, ty: 0 }
  window.addEventListener('pointermove', (e) => {
    pointer.tx = (e.clientX / window.innerWidth) * 2 - 1
    pointer.ty = (e.clientY / window.innerHeight) * 2 - 1
  })

  let width = 1
  let height = 1
  let visW = 1
  let visH = 1
  function resize() {
    width = window.innerWidth
    height = window.innerHeight
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    visH = 2 * camera.position.z * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))
    visW = visH * camera.aspect
    renderer.setSize(width, height, false)
  }
  resize()
  window.addEventListener('resize', resize)

  const frameCallbacks = new Set()
  const timer = new THREE.Timer()

  function render() {
    timer.update()
    const dt = Math.min(timer.getDelta(), 0.05)
    const t = timer.getElapsed()
    const follow = 1 - Math.pow(0.001, dt) // frame-rate independent smoothing
    pointer.x += (pointer.tx - pointer.x) * follow
    pointer.y += (pointer.ty - pointer.y) * follow

    const intro = 1 - Math.pow(1 - state.intro, 3)
    const fit = Math.min(1, visW / 4.2)
    const float = reduced ? 0 : Math.sin(t * 0.8) * 0.05
    const sway = reduced ? 0 : Math.sin(t * 0.35) * 0.3 * state.idle

    rig.position.set((state.vx * visW) / 2, (state.vy * visH) / 2 + float, 0)
    rig.scale.setScalar(state.scale * fit * (0.55 + 0.45 * intro))
    rig.rotation.set(state.rotX, state.rotY + sway + (1 - intro) * -1.8, state.rotZ)
    if (!reduced) tilt.rotation.set(pointer.y * 0.16, pointer.x * 0.24, 0)

    watch?.update(t, state.explode)
    frameCallbacks.forEach((cb) => cb(t))
    renderer.render(scene, camera)
  }
  gsap.ticker.add(render)

  const v = new THREE.Vector3()
  function project(object) {
    object.getWorldPosition(v).project(camera)
    return { x: (v.x * 0.5 + 0.5) * width, y: (-v.y * 0.5 + 0.5) * height }
  }

  return {
    state,
    anchors: null,
    project,
    setFinish: (name) => watch?.setFinish(name),
    async load(onProgress) {
      watch = await loadWatch(renderer, onProgress)
      this.root = watch.root
      tilt.add(watch.root)
      this.anchors = watch.anchors
      await renderer.compileAsync(scene, camera)
    },
    onFrame(cb) {
      frameCallbacks.add(cb)
      return () => frameCallbacks.delete(cb)
    },
  }
}
