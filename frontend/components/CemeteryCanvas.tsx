"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Sparkles, Text } from "@react-three/drei";
import { useMemo, useRef, useState } from "react";
import type { Mesh } from "three";
import type { Grave } from "@/lib/types";

const BROKEN = "#ff1a1a";
const RESTABLE = "#6fb7ff";

function Gravestone({ grave, position, onSelect }: { grave: Grave; position: [number, number, number]; onSelect: (g: Grave) => void }) {
  const ref = useRef<Mesh>(null);
  const [hover, setHover] = useState(false);
  const broken = grave.status === "broken";
  const color = broken ? BROKEN : RESTABLE;
  const height = 1.2 + Math.min(grave.staleness_days, 1200) / 1200;

  useFrame(({ clock }) => {
    const m = ref.current?.material as { emissiveIntensity: number } | undefined;
    if (!m) return;
    const pulse = broken ? 0.7 + 0.5 * Math.sin(clock.elapsedTime * 3) : 0.5;
    m.emissiveIntensity = pulse + (hover ? 0.8 : 0);
  });

  return (
    <group position={position}>
      <mesh
        ref={ref}
        position={[0, height / 2, 0]}
        onPointerOver={(e) => { e.stopPropagation(); setHover(true); document.body.style.cursor = "pointer"; }}
        onPointerOut={() => { setHover(false); document.body.style.cursor = "auto"; }}
        onClick={(e) => { e.stopPropagation(); onSelect(grave); }}
      >
        <boxGeometry args={[1, height, 0.25]} />
        <meshStandardMaterial color="#2a2a30" emissive={color} emissiveIntensity={0.6} roughness={0.9} />
      </mesh>
      <mesh position={[0, height, 0]}>
        <cylinderGeometry args={[0.5, 0.5, 0.25, 24, 1, false, 0, Math.PI]} />
        <meshStandardMaterial color="#2a2a30" emissive={color} emissiveIntensity={0.6} roughness={0.9} />
      </mesh>
      <pointLight color={color} intensity={hover ? 3 : 1.2} distance={4} position={[0, height / 2, 0.8]} />
      <Text position={[0, 0.15, 0.3]} fontSize={0.12} color="#e8d9b0" maxWidth={0.9} anchorY="bottom" rotation={[-0.3, 0, 0]}>
        {grave.branch}
      </Text>
    </group>
  );
}

export default function CemeteryCanvas({ graves, onSelect, haunted }: { graves: Grave[]; onSelect: (g: Grave) => void; haunted: boolean }) {
  const positions = useMemo(
    () =>
      graves.map((_, i): [number, number, number] => {
        const cols = Math.ceil(Math.sqrt(graves.length));
        return [(i % cols) * 2.6 - ((cols - 1) * 2.6) / 2, 0, Math.floor(i / cols) * 2.8 - 1];
      }),
    [graves],
  );

  return (
    <Canvas camera={{ position: [0, 4, 9], fov: 55 }} shadows>
      <color attach="background" args={[haunted ? "#1a0505" : "#07070d"]} />
      <fog attach="fog" args={[haunted ? "#2a0808" : "#0b0b16", 6, 22]} />
      <ambientLight intensity={0.25} color="#ffb870" />
      <directionalLight position={[3, 8, 2]} intensity={0.4} color="#aab8ff" />
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[60, 60]} />
        <meshStandardMaterial color="#101410" roughness={1} />
      </mesh>
      {graves.map((g, i) => (
        <Gravestone key={g.branch} grave={g} position={positions[i]} onSelect={onSelect} />
      ))}
      <Sparkles count={80} scale={[16, 6, 12]} size={3} speed={0.3} color={haunted ? "#ff4040" : "#ffcf7a"} />
      <OrbitControls maxPolarAngle={Math.PI / 2.1} minDistance={4} maxDistance={18} />
    </Canvas>
  );
}
