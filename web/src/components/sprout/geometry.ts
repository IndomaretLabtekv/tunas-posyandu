import * as THREE from "three";

export type SproutParts = {
  group: THREE.Group;
  soil: THREE.Mesh<THREE.SphereGeometry, THREE.MeshPhysicalMaterial>;
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
    const arch = Math.sin((x / 1.55) * Math.PI) * 0.12;
    positions.setZ(index, arch + y * 0.08);
  }

  positions.needsUpdate = true;
  geometry.computeVertexNormals();
  return geometry;
}

export function createSproutParts(compact: boolean): SproutParts {
  const group = new THREE.Group();
  const soilMaterial = new THREE.MeshPhysicalMaterial({
    color: 0x4b2418,
    roughness: 0.55,
    clearcoat: 0.18,
    transparent: true,
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
    new THREE.TubeGeometry(
      path,
      compact ? 40 : 64,
      0.095,
      compact ? 8 : 12,
      false,
    ),
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

  leafGeometry.dispose();
  leafMaterial.dispose();

  group.add(soil, stem, leftLeaf, rightLeaf);
  group.rotation.y = -0.18;

  return { group, soil, stem, leftLeaf, rightLeaf };
}
