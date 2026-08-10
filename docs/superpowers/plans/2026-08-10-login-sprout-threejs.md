# Animated Three.js Login Sprout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight procedural 3D sprout to the Tunas login that grows once, idles calmly, and remains usable as a mobile PWA.

**Architecture:** Isolate all Three.js work in a dynamically imported client component so only the login route loads the 3D bundle. Build the soil, stem, and leaves from procedural geometry, animate them with one requestAnimationFrame loop, and preserve authentication as a separate concern. Provide reduced-motion, hidden-tab, resize, cleanup, and WebGL-failure behavior inside the scene boundary.

**Tech Stack:** Next.js 15, React 19, TypeScript, vanilla Three.js, Tailwind CSS 3, Next dynamic imports.

---

## File Map

- Create `web/src/components/sprout/geometry.ts`: procedural soil, stem, leaf, and material factories.
- Create `web/src/components/SproutScene.tsx`: renderer lifecycle, responsive quality, animation, fallback, and cleanup.
- Modify `web/src/app/login/page.tsx`: dynamic scene loading and responsive split login layout.
- Modify `web/package.json` and `web/package-lock.json`: add `three` and `@types/three`.

### Task 1: Add the Three.js Dependency

**Files:**
- Modify: `web/package.json`
- Modify: `web/package-lock.json`

- [ ] **Step 1: Install runtime and TypeScript packages**

Run:

```bash
rtk npm install three --prefix web
rtk npm install --save-dev @types/three --prefix web
```

Expected: `three` appears in `dependencies`, `@types/three` appears in `devDependencies`, and the npm lock records both packages.

- [ ] **Step 2: Inspect dependency scope**

Run:

```bash
rtk rg -n '"three"|"@types/three"' web/package.json web/package-lock.json
```

Expected: no application file imports Three.js yet.

### Task 2: Build Procedural Sprout Geometry

**Files:**
- Create: `web/src/components/sprout/geometry.ts`

- [ ] **Step 1: Add focused geometry factories**

Implement these exported contracts:

```ts
import * as THREE from "three";

export type SproutParts = {
  group: THREE.Group;
  soil: THREE.Mesh;
  stem: THREE.Mesh<THREE.TubeGeometry, THREE.MeshPhysicalMaterial>;
  leftLeaf: THREE.Mesh<THREE.ShapeGeometry, THREE.MeshPhysicalMaterial>;
  rightLeaf: THREE.Mesh<THREE.ShapeGeometry, THREE.MeshPhysicalMaterial>;
};

function createLeafGeometry(detail: number): THREE.ShapeGeometry {
  const shape = new THREE.Shape();
  shape.moveTo(0, 0);
  shape.bezierCurveTo(0.35, 0.42, 1.05, 0.55, 1.55, 0.08);
  shape.bezierCurveTo(1.05, -0.18, 0.38, -0.15, 0, 0);
  const geometry = new THREE.ShapeGeometry(shape, detail);
  const positions = geometry.attributes.position;
  for (let index = 0; index < positions.count; index += 1) {
    const x = positions.getX(index);
    const y = positions.getY(index);
    positions.setZ(index, Math.sin((x / 1.55) * Math.PI) * 0.12 + y * 0.08);
  }
  geometry.computeVertexNormals();
  return geometry;
}

export function createSproutParts(compact: boolean): SproutParts {
  const group = new THREE.Group();
  const soilMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x4b2418,
    roughness: 0.55,
    clearcoat: 0.18,
  });
  const stemMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x9a4523,
    roughness: 0.46,
    clearcoat: 0.22,
  });
  const leafMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x55d82d,
    roughness: 0.35,
    clearcoat: 0.55,
    clearcoatRoughness: 0.2,
    side: THREE.DoubleSide,
  });

  const soil = new THREE.Mesh(
    new THREE.SphereGeometry(1.42, compact ? 32 : 48, compact ? 14 : 20),
    soilMaterial,
  );
  soil.scale.set(1.15, 0.28, 0.82);
  soil.position.y = -0.35;

  const path = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, -0.2, 0),
    new THREE.Vector3(-0.04, 0.45, 0.01),
    new THREE.Vector3(0.08, 1.15, 0),
    new THREE.Vector3(-0.03, 1.85, 0.02),
  ]);
  const stem = new THREE.Mesh(
    new THREE.TubeGeometry(path, compact ? 40 : 64, 0.095, compact ? 8 : 12, false),
    stemMaterial,
  );

  const leafGeometry = createLeafGeometry(compact ? 6 : 10);
  const leftLeaf = new THREE.Mesh(leafGeometry.clone(), leafMaterial.clone());
  leftLeaf.position.set(0.02, 1.48, 0);
  leftLeaf.rotation.set(-0.08, -0.2, 2.72);
  leftLeaf.scale.setScalar(0.78);

  const rightLeaf = new THREE.Mesh(leafGeometry.clone(), leafMaterial.clone());
  rightLeaf.position.set(0.01, 1.18, 0.02);
  rightLeaf.rotation.set(0.08, 0.18, -0.18);

  group.add(soil, stem, leftLeaf, rightLeaf);
  group.rotation.y = -0.18;
  return { group, soil, stem, leftLeaf, rightLeaf };
}
```

- [ ] **Step 2: Keep animation state out of geometry factories**

Confirm `geometry.ts` contains no renderer, DOM, React, timing, pointer, or window access. All returned geometries and materials must be independently disposable by the scene component.

### Task 3: Implement the Scene Lifecycle and Growth Animation

**Files:**
- Create: `web/src/components/SproutScene.tsx`

- [ ] **Step 1: Create the client component boundary**

Use this public interface:

```tsx
"use client";

export default function SproutScene({ className = "" }: { className?: string }) {
  // A single mount ref, one failed-state fallback, and one lifecycle effect.
}
```

The rendered root must reserve its full size, be `aria-hidden="true"`, and show a cobalt radial-gradient fallback when WebGL cannot initialize.

- [ ] **Step 2: Initialize a transparent responsive scene**

Inside one `useEffect`, create:

```ts
const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.08;
renderer.setPixelRatio(Math.min(window.devicePixelRatio, compact ? 1.25 : 1.5));

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(31, 1, 0.1, 100);
camera.position.set(0.1, 1.0, compact ? 6.3 : 5.6);
camera.lookAt(0, 0.72, 0);

scene.add(new THREE.HemisphereLight(0xdbeafe, 0x3b2419, 2.2));
const key = new THREE.DirectionalLight(0xffffff, 3.2);
key.position.set(3, 5, 4);
scene.add(key);
const rim = new THREE.DirectionalLight(0x9dff72, 1.7);
rim.position.set(-4, 3, -2);
scene.add(rim);
```

Add `createSproutParts(compact).group`, append `renderer.domElement`, and use a `ResizeObserver` to update renderer size and camera aspect from the container's content rectangle.

- [ ] **Step 3: Implement grounded growth**

Use monotonic progress helpers:

```ts
const clamp01 = (value: number) => Math.min(1, Math.max(0, value));
const smooth = (value: number) => {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
};
```

At mount, set soil scale to 85%, stem draw range to zero, and leaf scales to zero. During the frame loop:

```ts
const soilProgress = smooth(elapsed / 0.65);
const stemProgress = smooth((elapsed - 0.22) / 2.38);
const leftProgress = smooth((elapsed - 1.38) / 0.9);
const rightProgress = smooth((elapsed - 1.66) / 0.9);

soil.scale.set(1.15 * (0.85 + 0.15 * soilProgress), 0.28 * (0.85 + 0.15 * soilProgress), 0.82 * (0.85 + 0.15 * soilProgress));
stem.geometry.setDrawRange(0, Math.floor(stem.geometry.index!.count * stemProgress));
leftLeaf.scale.setScalar(0.78 * leftProgress);
rightLeaf.scale.setScalar(rightProgress);

if (elapsed > 2.7) {
  const idle = elapsed - 2.7;
  group.rotation.z = Math.sin(idle * 0.52) * 0.008;
  leftLeaf.rotation.x = -0.08 + Math.sin(idle * 0.46) * 0.006;
  rightLeaf.rotation.x = 0.08 + Math.sin(idle * 0.43 + 0.8) * 0.006;
}
```

Render every active frame. Do not read pointer, touch, orientation, or gyroscope data.

- [ ] **Step 4: Honor reduced motion and tab visibility**

Read `window.matchMedia("(prefers-reduced-motion: reduce)")`. For reduced motion, immediately set the full stem draw range and final scales, render once, and do not schedule an idle loop.

Use `document.visibilitychange` to cancel the current animation frame while hidden and restart with adjusted elapsed time when visible, preventing a time jump and background battery use.

- [ ] **Step 5: Dispose every resource**

The effect cleanup must cancel animation frames, disconnect the observer, remove the visibility listener, traverse meshes to dispose geometries and all materials, dispose the renderer, call `renderer.forceContextLoss()`, and remove its canvas from the mount node.

Wrap renderer initialization in `try/catch`; on failure call `setFailed(true)` and leave the fallback visible.

### Task 4: Integrate the Scene Into the Login

**Files:**
- Modify: `web/src/app/login/page.tsx`

- [ ] **Step 1: Dynamically load the scene**

Add:

```tsx
import dynamic from "next/dynamic";

const SproutScene = dynamic(() => import("@/components/SproutScene"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse rounded-2xl bg-blue-900/20" />,
});
```

- [ ] **Step 2: Replace the centered form with a responsive split layout**

The page root stays `min-h-[100dvh]` with safe PWA padding. Use a maximum 1100-pixel container with:

```tsx
<div className="grid w-full max-w-6xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_24px_70px_rgba(29,48,85,0.12)] lg:grid-cols-[1.05fr_0.95fr]">
  <section className="relative min-h-[260px] overflow-hidden bg-gradient-to-br from-blue-950 via-blue-900 to-blue-700 p-6 text-white sm:min-h-[320px] sm:p-8 lg:min-h-[680px] lg:p-10">
    <div className="relative z-10 flex h-full flex-col justify-between">
      <Link href="/" className="focus-ring flex w-fit items-center gap-3 rounded-xl">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-white font-black text-blue-900">T</span>
        <span className="font-bold">Tunas</span>
      </Link>
      <div className="max-w-sm pb-[210px] sm:pb-[280px] lg:pb-0">
        <p className="text-sm font-semibold text-blue-200">Pemantauan pertumbuhan 0-23 bulan</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">Tumbuh bersama, dipantau bersama.</h1>
        <p className="mt-3 text-sm leading-6 text-blue-100">Satu alur untuk keluarga, kader, dan ahli gizi.</p>
      </div>
    </div>
    <SproutScene className="absolute inset-x-0 bottom-0 h-[230px] sm:h-[300px] lg:h-[500px]" />
  </section>
  <section className="p-6 sm:p-8 lg:p-10">
    {/* Preserve the current mode switch, fields, errors, and submit button here. */}
  </section>
</div>
```

Keep every existing state variable, submit branch, API call, error message, role redirect, input name, minimum password length, and button disabled behavior unchanged.

- [ ] **Step 3: Keep the form above the mobile fold**

On widths below `lg`, use a compact scene and concise copy. Do not place controls over the canvas. Keep all inputs at 16-pixel mobile font size through the existing global PWA rules and preserve 44-pixel touch targets.

### Task 5: Deferred Verification Gate

**Files:**
- Inspect: `web/src/components/SproutScene.tsx`
- Inspect: `web/src/components/sprout/geometry.ts`
- Inspect: `web/src/app/login/page.tsx`

These commands are documented but must not be run in the current execution because the user requested tests and builds later.

- [ ] **Step 1: Type and production build**

Run later:

```bash
rtk npm run build --prefix web
```

Expected: Next.js production build succeeds with no TypeScript error and only the login route references the dynamically split Three.js chunk.

- [ ] **Step 2: Browser acceptance**

Check later at mobile 390x844 and desktop 1440x900:

- soil, stem, and leaves complete their entrance once;
- the form remains usable while animation runs;
- reduced motion renders the final sprout immediately;
- resizing preserves aspect without layout shift;
- backgrounding the PWA pauses rendering;
- navigating away removes the WebGL canvas and context;
- login and mother registration still redirect by role;
- a forced WebGL failure leaves the form usable with the fallback panel.

- [ ] **Step 3: Commit implementation after deferred verification**

```bash
rtk git add web/package.json web/package-lock.json web/src/components/SproutScene.tsx web/src/components/sprout/geometry.ts web/src/app/login/page.tsx
rtk git commit -m "feat: animate login sprout with threejs"
```

Do not include unrelated workflow or UI files in this commit.
