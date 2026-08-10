"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { createSproutParts } from "@/components/sprout/geometry";

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

const smooth = (value: number) => {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
};

export default function SproutScene({ className = "" }: { className?: string }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    let renderer: THREE.WebGLRenderer | null = null;
    let resizeObserver: ResizeObserver | null = null;
    let frameId = 0;
    let disposed = false;
    let removeVisibilityListener = () => {};
    const scene = new THREE.Scene();

    try {
      const compact = window.matchMedia("(max-width: 767px)").matches;
      const reducedMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;

      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.08;
      renderer.setPixelRatio(
        Math.min(window.devicePixelRatio, compact ? 1.25 : 1.5),
      );
      renderer.domElement.className = "block h-full w-full";
      renderer.domElement.style.pointerEvents = "none";
      mount.appendChild(renderer.domElement);

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

      const { group, soil, stem, leftLeaf, rightLeaf } =
        createSproutParts(compact);
      scene.add(group);

      const stemCount =
        stem.geometry.index?.count ?? stem.geometry.attributes.position.count;
      const leftFinalRotation = leftLeaf.rotation.clone();
      const rightFinalRotation = rightLeaf.rotation.clone();

      const setFinalPose = () => {
        soil.scale.set(1.15, 0.28, 0.82);
        soil.material.opacity = 1;
        stem.geometry.setDrawRange(0, stemCount);
        leftLeaf.scale.setScalar(0.78);
        rightLeaf.scale.setScalar(1);
        leftLeaf.rotation.copy(leftFinalRotation);
        rightLeaf.rotation.copy(rightFinalRotation);
      };

      const resize = () => {
        if (!renderer) return;
        const { width, height } = mount.getBoundingClientRect();
        const safeWidth = Math.max(1, Math.round(width));
        const safeHeight = Math.max(1, Math.round(height));
        renderer.setSize(safeWidth, safeHeight, false);
        camera.aspect = safeWidth / safeHeight;
        camera.updateProjectionMatrix();
      };

      resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(mount);
      resize();

      if (reducedMotion) {
        setFinalPose();
        renderer.render(scene, camera);
      } else {
        soil.scale.set(1.15 * 0.85, 0.28 * 0.85, 0.82 * 0.85);
        soil.material.opacity = 0;
        stem.geometry.setDrawRange(0, 0);
        leftLeaf.scale.setScalar(0);
        rightLeaf.scale.setScalar(0);
        leftLeaf.rotation.z = leftFinalRotation.z - 0.42;
        rightLeaf.rotation.z = rightFinalRotation.z - 0.47;

        const startedAt = performance.now();
        let hiddenAt = 0;
        let pausedDuration = 0;

        const renderFrame = (now: number) => {
          if (disposed || document.hidden || !renderer) return;

          const elapsed = (now - startedAt - pausedDuration) / 1000;
          const soilProgress = smooth(elapsed / 0.65);
          const stemProgress = smooth((elapsed - 0.22) / 2.38);
          const leftProgress = smooth((elapsed - 1.38) / 0.9);
          const rightProgress = smooth((elapsed - 1.66) / 0.9);

          const soilScale = 0.85 + 0.15 * soilProgress;
          soil.scale.set(
            1.15 * soilScale,
            0.28 * soilScale,
            0.82 * soilScale,
          );
          soil.material.opacity = soilProgress;
          stem.geometry.setDrawRange(
            0,
            Math.floor(stemCount * stemProgress),
          );
          leftLeaf.scale.setScalar(0.78 * leftProgress);
          rightLeaf.scale.setScalar(rightProgress);
          leftLeaf.rotation.z = THREE.MathUtils.lerp(
            leftFinalRotation.z - 0.42,
            leftFinalRotation.z,
            leftProgress,
          );
          rightLeaf.rotation.z = THREE.MathUtils.lerp(
            rightFinalRotation.z - 0.47,
            rightFinalRotation.z,
            rightProgress,
          );

          if (elapsed > 2.7) {
            const idle = elapsed - 2.7;
            group.rotation.z = Math.sin(idle * 0.52) * 0.008;
            leftLeaf.rotation.x =
              leftFinalRotation.x + Math.sin(idle * 0.46) * 0.006;
            rightLeaf.rotation.x =
              rightFinalRotation.x + Math.sin(idle * 0.43 + 0.8) * 0.006;
          }

          renderer.render(scene, camera);
          frameId = window.requestAnimationFrame(renderFrame);
        };

        const onVisibilityChange = () => {
          if (document.hidden) {
            hiddenAt = performance.now();
            window.cancelAnimationFrame(frameId);
            frameId = 0;
            return;
          }

          if (hiddenAt > 0) {
            pausedDuration += performance.now() - hiddenAt;
            hiddenAt = 0;
          }
          frameId = window.requestAnimationFrame(renderFrame);
        };

        document.addEventListener("visibilitychange", onVisibilityChange);
        removeVisibilityListener = () =>
          document.removeEventListener("visibilitychange", onVisibilityChange);
        frameId = window.requestAnimationFrame(renderFrame);
      }
    } catch {
      setFailed(true);
    }

    return () => {
      disposed = true;
      window.cancelAnimationFrame(frameId);
      resizeObserver?.disconnect();
      removeVisibilityListener();

      scene.traverse((object) => {
        if (!(object instanceof THREE.Mesh)) return;
        object.geometry.dispose();
        const materials = Array.isArray(object.material)
          ? object.material
          : [object.material];
        materials.forEach((material) => material.dispose());
      });

      if (renderer) {
        const canvas = renderer.domElement;
        renderer.dispose();
        renderer.forceContextLoss();
        if (canvas.parentNode === mount) mount.removeChild(canvas);
      }
    };
  }, []);

  return (
    <div
      aria-hidden="true"
      className={`overflow-hidden bg-[radial-gradient(circle_at_50%_68%,rgba(96,165,250,0.2),transparent_48%)] ${className}`}
    >
      <div ref={mountRef} className="h-full w-full" />
      {failed && (
        <div className="absolute inset-x-[28%] bottom-[16%] h-12 rounded-[50%] bg-blue-300/10 blur-xl" />
      )}
    </div>
  );
}
