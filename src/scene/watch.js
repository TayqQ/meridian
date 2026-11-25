// Loads the Blender-built watch (blender/build_watch.py). The GLB carries the
// geometry and named nodes: part_* groups slide apart in the exploded view and
// spin_* groups rotate. Materials are matched by name and replaced with tuned
// physical materials, so finishes can be swapped live.
import * as THREE from 'three'
import gsap from 'gsap'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js'

export const FINISHES = {
  gold: { label: '18k Gold', metal: '#f7d293', rough: 0.14, hand: '#ffdca6', dial: '#17130e', print: '#ebc68d', bg: '#0c0a08', accent: '#d9b27c', price: '£14,200' },
  steel: { label: 'Steel', metal: '#dfe2e6', rough: 0.16, hand: '#f4f6f9', dial: '#0f213d', print: '#e9eef5', bg: '#080b10', accent: '#a9c1e0', price: '£6,800' },
  black: { label: 'Black DLC', metal: '#3a3a3e', rough: 0.28, hand: '#e6c48c', dial: '#0b0b0b', print: '#d9b27c', bg: '#0a0a0a', accent: '#c9a36b', price: '£7,400' },
}

// [offset, delay, axis] for the exploded view. Parts keep their stacking order
// at every moment: outer layers travel further AND start sooner, so nothing
// can overtake (and pass through) the part outside it.
const PARTS = {
  // front, outermost first
  part_crystal: [2.6, 0],
  part_bezel: [2.0, 0.04],
  part_second: [1.55, 0.08],
  part_minute: [1.4, 0.1],
  part_hour: [1.25, 0.12],
  part_dial: [0.75, 0.16],
  // back, outermost first
  part_caseback: [-2.3, 0],
  part_rotor: [-1.75, 0.05],
  part_bridges: [-1.3, 0.1],
  part_balance: [-0.95, 0.15],
  part_gear4: [-0.94, 0.16],
  part_gear3: [-0.91, 0.16],
  part_gear2: [-0.88, 0.16],
  part_gear1: [-0.85, 0.16],
  part_plate: [-0.5, 0.2],
  // bracelet slides away along the wrist
  part_bracelet_top: [2.6, 0, 'y'],
  part_bracelet_bottom: [-2.6, 0, 'y'],
}
const GEAR_SPEEDS = { spin_gear1: 0.6, spin_gear2: -1.0, spin_gear3: 0.75, spin_gear4: -1.3 }

const TAU = Math.PI * 2
const clamp01 = (v) => Math.min(1, Math.max(0, v))
const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)

// Sunburst dials are brushed radially from the centre: encode that direction
// per pixel for MeshPhysicalMaterial.anisotropyMap (RG = direction, B = strength).
function radialAnisotropyMap(size = 512) {
  const c = document.createElement('canvas')
  c.width = c.height = size
  const g = c.getContext('2d')
  const img = g.createImageData(size, size)
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = ((x + 0.5) / size) * 2 - 1
      const dy = ((y + 0.5) / size) * 2 - 1
      const len = Math.hypot(dx, dy) || 1
      const i = (y * size + x) * 4
      img.data[i] = (dx / len) * 127.5 + 127.5
      img.data[i + 1] = (dy / len) * 127.5 + 127.5
      img.data[i + 2] = 255
      img.data[i + 3] = 255
    }
  }
  g.putImageData(img, 0, 0)
  const tex = new THREE.CanvasTexture(c)
  tex.flipY = false
  tex.colorSpace = THREE.NoColorSpace
  return tex
}

function loadNormal(loader, url) {
  const tex = loader.load(url)
  tex.flipY = false // glTF UV convention
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping
  tex.anisotropy = 8
  return tex
}

function createMaterials() {
  const f = FINISHES.gold
  const tl = new THREE.TextureLoader()
  const cotes = loadNormal(tl, '/models/textures/cotes.jpg')
  const perlage = loadNormal(tl, '/models/textures/perlage.jpg')
  const flipGreen = new THREE.Vector2(0.6, -0.6)

  return {
    case: new THREE.MeshPhysicalMaterial({ color: f.metal, metalness: 1, roughness: f.rough, clearcoat: 0.3, clearcoatRoughness: 0.1 }),
    bracelet_brushed: new THREE.MeshPhysicalMaterial({ color: f.metal, metalness: 1, roughness: f.rough + 0.2, anisotropy: 0.8, anisotropyRotation: Math.PI / 2, transparent: true }),
    bracelet_polished: new THREE.MeshPhysicalMaterial({ color: f.metal, metalness: 1, roughness: f.rough - 0.04, transparent: true }),
    hand: new THREE.MeshPhysicalMaterial({ color: f.hand, metalness: 1, roughness: 0.1 }),
    seconds: new THREE.MeshPhysicalMaterial({ color: '#c23a1e', metalness: 0, roughness: 0.3, clearcoat: 1, clearcoatRoughness: 0.05 }),
    dial: new THREE.MeshPhysicalMaterial({ color: f.dial, metalness: 0.75, roughness: 0.32, anisotropy: 0.9, anisotropyMap: radialAnisotropyMap(), clearcoat: 1, clearcoatRoughness: 0.04 }),
    print: new THREE.MeshPhysicalMaterial({ color: f.print, metalness: 0.8, roughness: 0.3 }),
    sapphire: new THREE.MeshPhysicalMaterial({ color: '#ffffff', metalness: 0, roughness: 0.02, transparent: true, opacity: 0.12, envMapIntensity: 2.2, clearcoat: 1, depthWrite: false }),
    rhodium_perlage: new THREE.MeshPhysicalMaterial({ color: '#d6d8dc', metalness: 1, roughness: 0.32, normalMap: perlage, normalScale: flipGreen }),
    rhodium_cotes: new THREE.MeshPhysicalMaterial({ color: '#dadce0', metalness: 1, roughness: 0.2, normalMap: cotes, normalScale: flipGreen }),
    gold_movement: new THREE.MeshPhysicalMaterial({ color: '#ebbd72', metalness: 1, roughness: 0.2 }),
    blued: new THREE.MeshPhysicalMaterial({ color: '#1b2f7a', metalness: 0.9, roughness: 0.2, iridescence: 1, iridescenceIOR: 2.0, iridescenceThicknessRange: [280, 360] }),
    ruby: new THREE.MeshPhysicalMaterial({ color: '#9b0d24', metalness: 0, roughness: 0.04, clearcoat: 1, specularIntensity: 1, ior: 1.77 }),
  }
}

// Instance the link prototypes onto the slot_* empties Blender laid out along the wrist.
function buildBracelet(root) {
  root.updateMatrixWorld(true)
  const proto = root.getObjectByName('proto_links')
  const meshes = []
  proto.traverse((o) => o.isMesh && meshes.push(o))
  proto.removeFromParent()

  for (const name of ['part_bracelet_top', 'part_bracelet_bottom']) {
    const group = root.getObjectByName(name)
    const slots = group.children.filter((o) => o.name.startsWith('slot_'))
    for (const src of meshes) {
      // keep the node transform: meshopt quantization stores the mesh's scale there
      const local = src.matrixWorld.clone()
      const inst = new THREE.InstancedMesh(src.geometry, src.material, slots.length)
      slots.forEach((slot, i) => inst.setMatrixAt(i, slot.matrix.clone().multiply(local)))
      inst.frustumCulled = false
      group.add(inst)
    }
    slots.forEach((slot) => slot.removeFromParent())
  }
}

export async function loadWatch(renderer, onProgress) {
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder)
  const gltf = await loader.loadAsync('/models/watch.glb', (e) => e.total && onProgress?.(e.loaded / e.total))
  const root = gltf.scene
  const mats = createMaterials()

  root.traverse((o) => {
    if (o.isMesh && mats[o.material.name]) o.material = mats[o.material.name]
  })
  buildBracelet(root)

  const node = (name) => root.getObjectByName(name)
  const parts = Object.entries(PARTS).map(([name, [offset, delay, axis = 'z']]) => ({ g: node(name), offset, delay, axis }))
  const gears = Object.entries(GEAR_SPEEDS).map(([name, speed]) => ({ spin: node(name), speed }))
  const hands = { hour: node('spin_hour'), minute: node('spin_minute'), second: node('spin_second') }
  const balance = node('spin_balance')
  const rotor = node('spin_rotor')
  const straps = [node('part_bracelet_top'), node('part_bracelet_bottom')]

  const anchor = (parent, x, y, z) => {
    const o = new THREE.Object3D()
    o.position.set(x, y, z)
    node(parent).add(o)
    return o
  }
  // Callout anchors sit on the top or bottom rim, matching each label's up/down leader line.
  const anchors = {
    crystal: anchor('part_crystal', 0, 1.0, 0.3),
    bezel: anchor('part_bezel', 0, -1.2, 0.26),
    hands: anchor('spin_minute', 0, 0.62, 0.01),
    dial: anchor('part_dial', 0, -0.95, 0.12),
    movement: anchor('part_gear3', 0.38, 0.56, -0.16),
    caseback: anchor('part_caseback', 0, -1.1, -0.24),
  }

  function update(t, explode) {
    const now = new Date()
    const s = now.getSeconds() + Math.floor(now.getMilliseconds() / 125) / 8
    const m = now.getMinutes() + s / 60
    const h = (now.getHours() % 12) + m / 60
    hands.second.rotation.z = -(s / 60) * TAU
    hands.minute.rotation.z = -(m / 60) * TAU
    hands.hour.rotation.z = -(h / 12) * TAU

    gears.forEach((g) => (g.spin.rotation.z = t * g.speed))
    balance.rotation.z = Math.sin(t * TAU * 2.5) * 1.4
    rotor.rotation.z = Math.sin(t * 0.4) * 1.6

    for (const p of parts) {
      p.g.position[p.axis] = p.offset * easeInOut(clamp01((explode - p.delay) / 0.6))
    }
    const strap = 1 - clamp01(explode * 1.8)
    mats.bracelet_brushed.opacity = mats.bracelet_polished.opacity = strap
    straps.forEach((g) => (g.visible = strap > 0.001))
  }

  function setFinish(name, duration = 1.2) {
    const fin = FINISHES[name]
    const tint = (mat, hex) => {
      const c = new THREE.Color(hex)
      gsap.to(mat.color, { r: c.r, g: c.g, b: c.b, duration, ease: 'power2.inOut', overwrite: true })
    }
    ;[mats.case, mats.bracelet_brushed, mats.bracelet_polished].forEach((m) => tint(m, fin.metal))
    tint(mats.hand, fin.hand)
    tint(mats.dial, fin.dial)
    tint(mats.print, fin.print)
    gsap.to(mats.case, { roughness: fin.rough, duration })
    gsap.to(mats.bracelet_polished, { roughness: fin.rough - 0.04, duration })
    gsap.to(mats.bracelet_brushed, { roughness: fin.rough + 0.2, duration })
  }

  return { root, anchors, update, setFinish }
}
