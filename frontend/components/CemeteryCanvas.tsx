"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Sparkles, Text } from "@react-three/drei";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { Grave } from "@/lib/types";

/** Restable: steady spectral glow. Broken (syntax rot): pulsing. */
export const RESTABLE_COLOR = 0x00aaff;
export const BROKEN_COLOR = 0xff1100;

const STONE = new THREE.Color(0x24262c);
const MOON_COLOR = new THREE.Color(0xcfe0ff);

type Vec3 = [number, number, number];

function Gravestone({
  grave,
  position,
  selected,
  onSelect,
}: {
  grave: Grave;
  position: Vec3;
  selected: boolean;
  onSelect: (g: Grave) => void;
}) {
  const bodyMat = useRef<THREE.MeshStandardMaterial>(null);
  const capMat = useRef<THREE.MeshStandardMaterial>(null);
  const light = useRef<THREE.PointLight>(null);
  const [hover, setHover] = useState(false);
  const broken = grave.status === "broken";
  const color = useMemo(() => new THREE.Color(broken ? BROKEN_COLOR : RESTABLE_COLOR), [broken]);
  const height = 1.2 + Math.min(grave.staleness_days, 1200) / 1200;

  useFrame(({ clock }) => {
    const base = broken ? 0.9 + 0.7 * Math.sin(clock.elapsedTime * 3) : 0.6;
    const boost = (hover ? 0.6 : 0) + (selected ? 0.9 : 0);
    const intensity = Math.max(0.1, base) + boost;
    for (const m of [bodyMat.current, capMat.current]) if (m) m.emissiveIntensity = intensity;
    if (light.current) light.current.intensity = (broken ? 1.4 + 1.0 * Math.sin(clock.elapsedTime * 3) : 1.6) + boost * 2;
  });

  return (
    <group position={position}>
      <mesh
        position={[0, height / 2, 0]}
        castShadow
        onPointerOver={(e) => {
          e.stopPropagation();
          setHover(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHover(false);
          document.body.style.cursor = "auto";
        }}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(grave);
        }}
      >
        <boxGeometry args={[1, height, 0.25]} />
        <meshStandardMaterial ref={bodyMat} color={STONE} emissive={color} emissiveIntensity={0.6} roughness={0.9} />
      </mesh>
      <mesh position={[0, height, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.5, 0.5, 0.25, 24, 1, false, Math.PI / 2, Math.PI]} />
        <meshStandardMaterial ref={capMat} color={STONE} emissive={color} emissiveIntensity={0.6} roughness={0.9} />
      </mesh>
      {selected && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 0.2]}>
          <ringGeometry args={[0.9, 1.05, 48]} />
          <meshBasicMaterial color={0x39ff14} transparent opacity={0.9} />
        </mesh>
      )}
      <pointLight ref={light} color={color} intensity={1.5} distance={4} position={[0, height / 2, 0.8]} />
      <Text position={[0, 0.15, 0.3]} fontSize={0.12} color={selected ? "#39ff14" : "#cbd5e1"} maxWidth={0.9} anchorY="bottom" rotation={[-0.3, 0, 0]}>
        {grave.branch}
      </Text>
    </group>
  );
}

function Moon({ haunted }: { haunted: boolean }) {
  const pos: Vec3 = [-14, 16, -22];
  return (
    <group>
      <mesh position={pos}>
        <sphereGeometry args={[2.2, 32, 32]} />
        <meshBasicMaterial color={haunted ? 0xff7766 : MOON_COLOR} fog={false} />
      </mesh>
      <mesh position={pos}>
        <sphereGeometry args={[3.2, 32, 32]} />
        <meshBasicMaterial color={0x88aaff} transparent opacity={0.12} fog={false} depthWrite={false} />
      </mesh>
      <directionalLight position={pos} intensity={1.3} color={haunted ? 0xff9988 : 0xb8ccff} castShadow shadow-mapSize={[1024, 1024]} />
      <spotLight position={[-8, 14, -6]} angle={0.7} penumbra={0.8} intensity={60} color={0xaac4ff} target-position={[0, 0, 0]} />
    </group>
  );
}

function Cross({ position, tilt }: { position: Vec3; tilt: number }) {
  return (
    <group position={position} rotation={[0, 0, tilt]}>
      <mesh position={[0, 0.9, 0]}>
        <boxGeometry args={[0.14, 1.8, 0.14]} />
        <meshStandardMaterial color={0x1b1d22} roughness={1} />
      </mesh>
      <mesh position={[0, 1.3, 0]}>
        <boxGeometry args={[0.8, 0.14, 0.14]} />
        <meshStandardMaterial color={0x1b1d22} roughness={1} />
      </mesh>
    </group>
  );
}

function DeadTree({ position, scale }: { position: Vec3; scale: number }) {
  const branches: Array<{ rot: number; len: number; y: number }> = [
    { rot: 0.8, len: 1.6, y: 2.2 },
    { rot: -0.9, len: 1.4, y: 2.8 },
    { rot: 0.5, len: 1.1, y: 3.4 },
    { rot: -0.6, len: 1.0, y: 1.6 },
  ];
  return (
    <group position={position} scale={scale}>
      <mesh position={[0, 2, 0]}>
        <cylinderGeometry args={[0.12, 0.3, 4, 8]} />
        <meshStandardMaterial color={0x15110f} roughness={1} />
      </mesh>
      {branches.map((b, i) => (
        <mesh key={i} position={[Math.sin(b.rot) * b.len * 0.5, b.y, 0]} rotation={[0, 0, -b.rot]}>
          <cylinderGeometry args={[0.03, 0.08, b.len, 6]} />
          <meshStandardMaterial color={0x15110f} roughness={1} />
        </mesh>
      ))}
    </group>
  );
}

function IronFence({ halfWidth, z }: { halfWidth: number; z: number }) {
  const count = Math.floor((halfWidth * 2) / 0.6);
  return (
    <group position={[0, 0, z]}>
      <mesh position={[0, 0.9, 0]}>
        <boxGeometry args={[halfWidth * 2, 0.06, 0.06]} />
        <meshStandardMaterial color={0x0c0d10} metalness={0.8} roughness={0.5} />
      </mesh>
      <mesh position={[0, 0.3, 0]}>
        <boxGeometry args={[halfWidth * 2, 0.06, 0.06]} />
        <meshStandardMaterial color={0x0c0d10} metalness={0.8} roughness={0.5} />
      </mesh>
      {Array.from({ length: count + 1 }, (_, i) => (
        <group key={i} position={[-halfWidth + i * 0.6, 0, 0]}>
          <mesh position={[0, 0.55, 0]}>
            <cylinderGeometry args={[0.03, 0.03, 1.1, 6]} />
            <meshStandardMaterial color={0x0c0d10} metalness={0.8} roughness={0.5} />
          </mesh>
          <mesh position={[0, 1.18, 0]}>
            <coneGeometry args={[0.06, 0.2, 6]} />
            <meshStandardMaterial color={0x0c0d10} metalness={0.8} roughness={0.5} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

function GroundFog({ haunted }: { haunted: boolean }) {
  const ref = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    if (ref.current) ref.current.position.x = Math.sin(clock.elapsedTime * 0.1) * 1.5;
  });
  return (
    <group ref={ref}>
      <Sparkles count={120} scale={[26, 0.8, 18]} position={[0, 0.4, 0]} size={14} speed={0.15} opacity={0.18} color={haunted ? 0xff5544 : 0x7f9fb8} />
    </group>
  );
}

export default function CemeteryCanvas({
  graves,
  selected,
  onSelect,
  haunted,
}: {
  graves: Grave[];
  selected: Grave | null;
  onSelect: (g: Grave | null) => void;
  haunted: boolean;
}) {
  const positions = useMemo(() => {
    const cols = Math.max(1, Math.ceil(Math.sqrt(graves.length)));
    return graves.map((_, i): Vec3 => [(i % cols) * 2.6 - ((cols - 1) * 2.6) / 2, 0, Math.floor(i / cols) * 2.8 - 1]);
  }, [graves]);

  return (
    <Canvas
      camera={{ position: [0, 4, 9], fov: 55 }}
      shadows
      onPointerMissed={() => onSelect(null)}
    >
      <color attach="background" args={[haunted ? "#1a0508" : "#05070c"]} />
      <fog attach="fog" args={[haunted ? "#2a0a10" : "#0a0f18", 6, 28]} />
      <ambientLight intensity={0.12} color={0x5a6a8a} />
      <Moon haunted={haunted} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[80, 80]} />
        <meshStandardMaterial color={0x0b100e} roughness={1} />
      </mesh>
      {graves.map((g, i) => (
        <Gravestone key={g.branch} grave={g} position={positions[i]} selected={selected?.branch === g.branch} onSelect={onSelect} />
      ))}
      <IronFence halfWidth={9} z={-6} />
      <Cross position={[-6, 0, 2]} tilt={0.12} />
      <Cross position={[6.5, 0, 3]} tilt={-0.18} />
      <Cross position={[-7.5, 0, -3]} tilt={0.05} />
      <DeadTree position={[-9, 0, -4]} scale={1.3} />
      <DeadTree position={[9, 0, -3]} scale={1.1} />
      <DeadTree position={[-4, 0, -8]} scale={1.6} />
      <GroundFog haunted={haunted} />
      <Sparkles count={60} scale={[16, 6, 12]} size={2.5} speed={0.3} color={haunted ? 0xff4040 : 0x39ff14} />
      <OrbitControls enableDamping dampingFactor={0.08} enablePan maxPolarAngle={Math.PI / 2.1} minDistance={4} maxDistance={18} />
    </Canvas>
  );
}
