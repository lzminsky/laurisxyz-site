/* The atlas — section 03's state space.
 *
 * ONE object, four states. Not four drawings.
 *
 *   i = the state of the world      (left <-> right)
 *   k = the route from exposure to ownership (back <-> front)
 *   h = payoff / exposure           (up)
 *
 *   I   Statebook   h = DIST[i]              payoff depends on the STATE only,
 *                                            so the field is uniform along k
 *   II  SLAM        h = SURF[i][k]           payoff now depends on state AND
 *                                            route — the field deforms
 *   III Hedgebook   h = SURF[i][k] * 0.3     settles into ground; exposures
 *                                            land on the cells that match
 *   IV  BizHedge    h = 0 except one cell    one exposure, funded + residual
 *
 * The I -> II morph is the argument, and it is one lerp: the route axis
 * turning on. Nothing crossfades — the same field changes height throughout.
 *
 * Driven by scroll position, never by a timer: there is no clock here, so a
 * transition cannot be interrupted, go stale, or snap.
 */
import {
  Scene, OrthographicCamera, WebGLRenderer, Fog, Color, Group,
  BoxGeometry, InstancedMesh, MeshStandardMaterial, Matrix4, Vector3,
  BufferGeometry, BufferAttribute, LineSegments, LineBasicMaterial,
  HemisphereLight, DirectionalLight, DoubleSide,
} from 'three';

const N = 12;                    // 13 x 13 field
const CELL = 1;
const clamp01 = (v) => Math.min(1, Math.max(0, v));
const smooth01 = (v) => { const t = clamp01(v); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;

/* ── the field ─────────────────────────────────────────────────────────── */

// Terminal payoff by state. Depends on i alone — that IS the statebook claim.
const DIST = [];
for (let i = 0; i <= N; i += 1) {
  DIST.push(0.22 + 5.4 * Math.exp(-((i - 4.4) ** 2) / 5.2) + 1.7 * Math.exp(-((i - 9.4) ** 2) / 3.4));
}
// Cost over (state, route). Depends on i AND k — that IS the SLAM claim.
const SURF = [];
for (let i = 0; i <= N; i += 1) {
  SURF.push([]);
  for (let k = 0; k <= N; k += 1) {
    SURF[i].push(
      2.8 * Math.exp(-(((i - 8.2) ** 2) / 8 + ((k - 3.4) ** 2) / 10)) +
      3.6 * Math.exp(-(((i - 2.8) ** 2) / 6 + ((k - 8.6) ** 2) / 8)) +
      0.55 * Math.sin(i * 0.9) * Math.cos(k * 0.7) + 0.5
    );
  }
}
// Corporate exposures and the cells they match (Plate III).
const SCATTER = [
  { i: 3, k: 9, ok: true }, { i: 5, k: 10, ok: true }, { i: 9, k: 8, ok: true },
  { i: 10, k: 5, ok: true }, { i: 6, k: 6, ok: true }, { i: 9, k: 11, ok: true },
  { i: 2, k: 4, ok: false }, { i: 5, k: 3, ok: false }, { i: 11, k: 9, ok: false },
];
const FOCUS = { i: 6, k: 6 };    // the one exposure at Plate IV
const EXPOSURE = 6.2;            // what the business is exposed to
const FUNDED = 3.6;              // what the contract actually pays

// Height of the column at (i,k) for a fractional station 0..3.
function heightAt(i, k, station) {
  const dist = DIST[i];
  const surf = SURF[i][k];
  if (station <= 1) {
    // I -> II: the route axis turns on. The whole argument, one lerp.
    return lerp(dist, surf, smooth01(station));
  }
  if (station <= 2) {
    // II -> III: the surface settles into ground to be read as a map.
    return lerp(surf, surf * 0.3, smooth01(station - 1));
  }
  // III -> IV: everything flattens but the one exposure.
  const t = smooth01(station - 2);
  const isFocus = i === FOCUS.i && k === FOCUS.k;
  return lerp(surf * 0.3, isFocus ? FUNDED : 0.02, t);
}

/* ── the camera: broad -> oblique -> plan -> close ──────────────────────
   define, price, map, act. The arc is the argument: a map IS a plan view,
   so the camera makes the claim before the copy does. */
const POSES = [
  { az: -0.52, el: 0.46, zoom: 1.00, tx: 0,   ty: 1.4, tz: 0 },    // I  broad
  { az: -0.98, el: 0.30, zoom: 1.04, tx: 0,   ty: 1.2, tz: 0 },    // II oblique
  { az: -0.72, el: 0.92, zoom: 0.90, tx: 0,   ty: 0.4, tz: 0 },    // III near-plan
  { az: -0.40, el: 0.22, zoom: 2.30, tx: 0.6, ty: 1.8, tz: 0.6 },  // IV close
];
const MOBILE_ZOOM = 0.78;

function poseAt(station) {
  const i = Math.min(POSES.length - 2, Math.floor(station));
  const t = smooth01(clamp01(station - i));
  const a = POSES[i], b = POSES[i + 1];
  return {
    az: lerp(a.az, b.az, t), el: lerp(a.el, b.el, t), zoom: lerp(a.zoom, b.zoom, t),
    tx: lerp(a.tx, b.tx, t), ty: lerp(a.ty, b.ty, t), tz: lerp(a.tz, b.tz, t),
  };
}

/* ── palette read off the canvas, so CSS drives the scene ───────────────── */
function palette(canvas) {
  const cs = getComputedStyle(canvas);
  const read = (name, fallback) => {
    const v = cs.getPropertyValue(name).trim();
    return new Color(v || fallback);
  };
  return {
    ink: read('--ink', '#181713'),
    paper: read('--paper', '#f1ece3'),
    teal: read('--teal', '#0e6670'),
    wine: read('--wine', '#78384f'),
    rule: read('--rule', '#d4ccc0'),
  };
}

// Pixel-budget DPR cap, from hpccc: cheaper than a flat clamp on big canvases.
function pixelRatio(w, h) {
  return Math.min(window.devicePixelRatio || 1, 1.75, Math.sqrt(3_600_000 / Math.max(1, w * h)));
}

export function createAtlas(canvas, { reducedMotion = false } = {}) {
  const C = palette(canvas);
  const renderer = new WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' });
  renderer.setClearAlpha(0);

  const scene = new Scene();
  // Semantic, not atmosphere: the far side of the state space is less certain.
  scene.fog = new Fog(C.paper.getHex(), 26, 62);

  const camera = new OrthographicCamera(-1, 1, 1, -1, 0.1, 200);
  const world = new Group();
  scene.add(world);

  scene.add(new HemisphereLight(0xffffff, C.paper.getHex(), 1.9));
  const key = new DirectionalLight(0xffffff, 1.5);
  key.position.set(6, 12, 8);
  scene.add(key);

  /* solids: paper, roughness high — never glossy */
  const COUNT = (N + 1) * (N + 1);
  const boxGeo = new BoxGeometry(CELL * 0.82, 1, CELL * 0.82);
  boxGeo.translate(0, 0.5, 0);                       // grow upward from the floor
  const paperMat = new MeshStandardMaterial({
    color: C.paper.clone().multiplyScalar(1.04), roughness: 0.94, metalness: 0,
    transparent: true, opacity: 0.96,
  });
  const cols = new InstancedMesh(boxGeo, paperMat, COUNT);
  world.add(cols);

  const focusMat = new MeshStandardMaterial({ color: C.wine, roughness: 0.9, metalness: 0, transparent: true, opacity: 0.5 });
  const focusCol = new InstancedMesh(boxGeo, focusMat, 1);
  world.add(focusCol);

  /* edges: the ink. This is the whole aesthetic — paper solid, drawn edge. */
  const EDGES_PER_COL = 8;                            // top rect (4) + verticals (4)
  const edgePos = new Float32Array(COUNT * EDGES_PER_COL * 2 * 3);
  const edgeGeo = new BufferGeometry();
  edgeGeo.setAttribute('position', new BufferAttribute(edgePos, 3));
  const edges = new LineSegments(edgeGeo, new LineBasicMaterial({
    color: C.ink, transparent: true, opacity: 0.42,
  }));
  world.add(edges);

  /* floor grid */
  const gridPts = [];
  for (let g = 0; g <= N; g += 1) {
    gridPts.push(g - N / 2, 0, -N / 2, g - N / 2, 0, N / 2);
    gridPts.push(-N / 2, 0, g - N / 2, N / 2, 0, g - N / 2);
  }
  const grid = new LineSegments(
    new BufferGeometry().setAttribute('position', new BufferAttribute(new Float32Array(gridPts), 3)),
    new LineBasicMaterial({ color: C.ink, transparent: true, opacity: 0.12 })
  );
  world.add(grid);

  /* Plate III: the cells that matched, and the exposures that found them */
  const markPos = new Float32Array(SCATTER.length * 8 * 2 * 3);
  const markGeo = new BufferGeometry();
  markGeo.setAttribute('position', new BufferAttribute(markPos, 3));
  const marks = new LineSegments(markGeo, new LineBasicMaterial({ color: C.teal, transparent: true, opacity: 0 }));
  world.add(marks);

  /* Plate IV: the residual — what the hedge does NOT cover, left visible */
  const resPos = new Float32Array(9 * 2 * 3);
  const resGeo = new BufferGeometry();
  resGeo.setAttribute('position', new BufferAttribute(resPos, 3));
  const residual = new LineSegments(resGeo, new LineBasicMaterial({ color: C.wine, transparent: true, opacity: 0 }));
  world.add(residual);

  const m4 = new Matrix4();
  const v3 = new Vector3();
  let w = 0, h = 0, station = 0, breathe = 0;

  const setEdge = (arr, n, ax, ay, az2, bx, by, bz) => {
    const o = n * 6;
    arr[o] = ax; arr[o + 1] = ay; arr[o + 2] = az2;
    arr[o + 3] = bx; arr[o + 4] = by; arr[o + 5] = bz;
  };

  function build(st) {
    const half = N / 2;
    const hw = CELL * 0.41;
    let e = 0;
    let n = 0;
    for (let i = 0; i <= N; i += 1) {
      for (let k = 0; k <= N; k += 1) {
        const x = i - half, z = k - half;
        const isFocus = i === FOCUS.i && k === FOCUS.k;
        let hh = Math.max(0.015, heightAt(i, k, st));
        // The SLAM idle rule, stolen wholesale: at Plate IV the funded payoff
        // breathes and the residual does not move at all — because nothing is
        // protecting it. The animation is the argument.
        if (isFocus && st > 2.8) hh *= 1 + breathe * 0.015;

        m4.makeScale(1, hh, 1);
        m4.setPosition(x, 0, z);
        cols.setMatrixAt(n, m4);
        if (isFocus) focusCol.setMatrixAt(0, m4);

        // top rectangle + four verticals
        const y = hh;
        setEdge(edgePos, e++, x - hw, y, z - hw, x + hw, y, z - hw);
        setEdge(edgePos, e++, x + hw, y, z - hw, x + hw, y, z + hw);
        setEdge(edgePos, e++, x + hw, y, z + hw, x - hw, y, z + hw);
        setEdge(edgePos, e++, x - hw, y, z + hw, x - hw, y, z - hw);
        setEdge(edgePos, e++, x - hw, 0, z - hw, x - hw, y, z - hw);
        setEdge(edgePos, e++, x + hw, 0, z - hw, x + hw, y, z - hw);
        setEdge(edgePos, e++, x + hw, 0, z + hw, x + hw, y, z + hw);
        setEdge(edgePos, e++, x - hw, 0, z + hw, x - hw, y, z + hw);
        n += 1;
      }
    }
    cols.instanceMatrix.needsUpdate = true;
    focusCol.instanceMatrix.needsUpdate = true;
    edgeGeo.attributes.position.needsUpdate = true;
    edgeGeo.computeBoundingSphere();

    // Plate III marks: matched cells get a box, unmatched a dashed-looking stub.
    const showMarks = clamp01(1 - Math.abs(st - 2) * 1.3);
    marks.material.opacity = showMarks * 0.75;
    if (showMarks > 0.01) {
      let mi = 0;
      for (const s of SCATTER) {
        const x = s.i - half, z = s.k - half;
        const y = Math.max(0.02, heightAt(s.i, s.k, st)) + 0.04;
        const r = s.ok ? 0.42 : 0.22;
        setEdge(markPos, mi++, x - r, y, z - r, x + r, y, z - r);
        setEdge(markPos, mi++, x + r, y, z - r, x + r, y, z + r);
        setEdge(markPos, mi++, x + r, y, z + r, x - r, y, z + r);
        setEdge(markPos, mi++, x - r, y, z + r, x - r, y, z - r);
        // the exposure descending onto the cell it matched
        const drop = s.ok ? 2.6 : 1.1;
        setEdge(markPos, mi++, x, y, z, x, y + drop, z);
        setEdge(markPos, mi++, x - 0.1, y + drop, z, x + 0.1, y + drop, z);
        setEdge(markPos, mi++, x, y + drop, z - 0.1, x, y + drop, z + 0.1);
        setEdge(markPos, mi++, x, y, z, x, y, z);
      }
      markGeo.attributes.position.needsUpdate = true;
      markGeo.computeBoundingSphere();
    }

    // Plate IV: the residual, hatched between what pays and what you're exposed to.
    const showRes = clamp01((st - 2.35) * 1.6);
    residual.material.opacity = showRes * 0.8;
    focusMat.opacity = showRes * 0.55;
    if (showRes > 0.01) {
      const x = FOCUS.i - half, z = FOCUS.k - half;
      let ri = 0;
      for (let j = 0; j < 8; j += 1) {
        const y = FUNDED + 0.3 + j * ((EXPOSURE - FUNDED) / 8);
        setEdge(resPos, ri++, x - hw, y, z + hw, x + hw, y - 0.18, z + hw);
      }
      setEdge(resPos, ri++, x - hw, EXPOSURE, z + hw, x + hw, EXPOSURE, z + hw);
      resGeo.attributes.position.needsUpdate = true;
      resGeo.computeBoundingSphere();
    }
  }

  function place(st) {
    const p = poseAt(st);
    const dist = 40;
    const ce = Math.cos(p.el), se = Math.sin(p.el);
    camera.position.set(
      p.tx + dist * ce * Math.sin(p.az),
      p.ty + dist * se,
      p.tz + dist * ce * Math.cos(p.az)
    );
    camera.lookAt(p.tx, p.ty, p.tz);
    const aspect = w / Math.max(1, h);
    const mobile = w < 640;
    const view = (N * 0.86) / (p.zoom * (mobile ? MOBILE_ZOOM : 1));
    camera.left = -view * aspect; camera.right = view * aspect;
    camera.top = view; camera.bottom = -view;
    camera.updateProjectionMatrix();
  }

  function resize() {
    const r = canvas.getBoundingClientRect();
    if (!r.width || !r.height) return false;
    w = r.width; h = r.height;
    renderer.setPixelRatio(pixelRatio(w, h));
    renderer.setSize(w, h, false);
    return true;
  }

  function render(st, t = 0) {
    station = Math.min(3, Math.max(0, st));
    breathe = reducedMotion ? 0 : Math.sin(t * 0.0016);
    build(station);
    place(station);
    renderer.render(scene, camera);
  }

  function dispose() {
    world.traverse((o) => {
      o.geometry?.dispose?.();
      const m = o.material;
      if (Array.isArray(m)) m.forEach((x) => x.dispose?.());
      else m?.dispose?.();
    });
    boxGeo.dispose();
    renderer.dispose();
    try { renderer.forceContextLoss(); } catch {}
  }

  resize();
  return { render, resize, dispose, get station() { return station; } };
}

// esbuild IIFE entry: expose the factory to the page.
window.__atlas = { createAtlas };
