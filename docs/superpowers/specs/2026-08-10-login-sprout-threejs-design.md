# Three.js Login Sprout Design

## Goal

Turn the Tunas login into a memorable PWA entry screen with a lightweight 3D sprout that grows once, then rests calmly while the user completes authentication.

## Confirmed Direction

- Use vanilla Three.js, not React Three Fiber or an external GLTF model.
- Match the reference image's friendly glossy 3D character without copying its stock watermark or exact asset.
- Use the selected grounded-growth sequence: soil appears, stem grows for about 2.6 seconds, leaves unfold, then the plant enters a nearly static breathing idle.
- Do not use pointer tracking, gyroscope input, ambient particles, or continuous camera movement.
- Keep the existing login and mother-registration behavior unchanged.

## Architecture

Create `web/src/components/SproutScene.tsx` as an isolated client component. It owns the Three.js renderer, scene, camera, lights, geometry, animation state, resize handling, visibility handling, and cleanup. The login page owns only form state and authentication.

Load the scene dynamically from the login page with server rendering disabled. Other routes must not import Three.js or include the scene bundle.

The scene uses project-local procedural geometry:

- a flattened glossy soil mound;
- a tapered curved stem built from a tube curve;
- two leaf meshes shaped from buffer geometry and slightly curved;
- soft hemisphere, key, and rim lighting;
- a transparent WebGL canvas over the login visual panel.

No external 3D files, textures, image downloads, or model loader are required.

## Motion

The entrance is deterministic and plays once per component mount:

1. Soil scales from 85% to 100% with a short opacity fade.
2. Stem draw range or vertical growth advances from the mound to full height over about 2.6 seconds.
3. Leaves scale and rotate open with a short stagger after the stem reaches their attachment points.
4. Camera and lights remain fixed throughout.
5. Idle motion is limited to a sub-degree stem sway and subtle leaf rotation with a long period.

When `prefers-reduced-motion` is enabled, render the complete sprout immediately and disable idle animation.

## Responsive Login Layout

Desktop uses a two-column surface: the sprout and product message occupy the visual side, while the form remains a focused white panel. The canvas receives a stable reserved area to avoid layout shift.

Mobile uses a single column. The 3D scene becomes a compact top visual, the form remains visible in the initial scroll area, controls keep at least 44-pixel touch targets, and safe-area padding remains active in standalone PWA mode. The scene reduces pixel ratio and geometry detail on small screens.

## Performance and Lifecycle

- Cap device pixel ratio at 1.5 on desktop and 1.25 on mobile.
- Pause the animation loop when the document is hidden.
- Stop rendering after the entrance when reduced motion is active.
- Use `ResizeObserver` instead of window resize polling.
- Dispose geometry, materials, renderer, observers, and animation frames on unmount.
- Use WebGL antialiasing only at the capped pixel ratio.
- If WebGL initialization fails, show a CSS gradient visual panel and keep the form fully usable.

## Visual Language

The sprout uses vivid lime-to-green leaves, a warm brown stem and soil, and soft studio highlights. The surrounding panel stays within the new cool-gray and cobalt Tunas interface so the green object becomes the focal point. No text overlays the canvas.

## Verification Scope

Automated tests and the production build remain deferred per the user's earlier instruction. Implementation should still include deterministic component boundaries and a non-WebGL fallback so those checks can be added later without redesigning the scene.
