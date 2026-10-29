// An interactive 3D model of the user's build, made with react-three-fiber (MIT) and drei (MIT).
// Each part is a simple shape placed where it really sits in a case. The parts fly in
// from an "exploded" view when the build appears. Hover a part to see what it is;
// click it to tell Python (setTriggerValue "selected"), which shows that part's details.
import { useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { ContactShadows, Edges, Html, OrbitControls, RoundedBox } from "@react-three/drei";
import * as THREE from "three";

const NEW_COLOUR = "#4fd1ff";
const USED_COLOUR = "#ffb547";
const SELECTED_COLOUR = "#b38cff";

// Case interior: x = front (+) to back (-), y = up, z = glass side (+) to motherboard tray (-).
const LAYOUT = {
  Motherboard: { pos: [-0.15, 0.25, -0.42], from: [-0.15, 0.25, -2.2] },
  CPU:         { pos: [-0.25, 0.75, -0.36], from: [-0.25, 2.4, -0.36] },
  Cooler:      { pos: [-0.25, 0.75, -0.12], from: [-0.25, 0.75, 1.8] },
  RAM:         { pos: [0.22, 0.75, -0.33], from: [0.22, 2.6, -0.33] },
  Storage:     { pos: [-0.2, 0.22, -0.37], from: [-2.4, 0.22, -0.37] },
  GPU:         { pos: [-0.12, -0.05, -0.12], from: [2.4, -0.05, -0.12] },
  PSU:         { pos: [-0.45, -0.95, -0.05], from: [-0.45, -2.6, -0.05] },
  Case:        { pos: [0, 0, 0], from: [0, 0, 0] },
};

function partColour(part, selected, hovered) {
  if (selected) return SELECTED_COLOUR;
  if (hovered) return "#c8f1ff";
  return part.condition === "Used" ? USED_COLOUR : NEW_COLOUR;
}

// Moves a part from its exploded position to its place, with a little stagger.
function Slot({ part, index, animate, selected, onSelect, children }) {
  const group = useRef();
  const start = useRef(null);
  const [hovered, setHovered] = useState(false);
  const { pos, from } = LAYOUT[part.category] || LAYOUT.Case;

  useFrame(({ clock }) => {
    if (!group.current) return;
    if (start.current === null) start.current = clock.elapsedTime + index * 0.12;
    const t = animate ? THREE.MathUtils.clamp((clock.elapsedTime - start.current) / 0.9, 0, 1) : 1;
    const ease = 1 - Math.pow(1 - t, 3);
    group.current.position.set(
      THREE.MathUtils.lerp(from[0], pos[0], ease),
      THREE.MathUtils.lerp(from[1], pos[1], ease),
      THREE.MathUtils.lerp(from[2], pos[2], ease));
  });

  const colour = partColour(part, selected, hovered);
  return (
    <group ref={group} position={from}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = "pointer"; }}
      onPointerOut={() => { setHovered(false); document.body.style.cursor = ""; }}
      onClick={(e) => { e.stopPropagation(); onSelect(part.category); }}>
      {children(colour, hovered || selected)}
      {(hovered || selected) && (
        <Html position={[0, 0.45, 0.3]} center distanceFactor={4.5} zIndexRange={[20, 0]}>
          <div className="rig-tag">
            <b>{part.category}</b> {part.name}
            <span>{part.condition} · {part.seller} · £{part.price.toFixed(0)}</span>
          </div>
        </Html>
      )}
    </group>
  );
}

// A dark body with a glowing edge in the part's colour.
function Block({ size, colour, glow, radius = 0.02, position, rotation, metal = 0.6 }) {
  return (
    <RoundedBox args={size} radius={radius} smoothness={3} position={position} rotation={rotation}>
      <meshStandardMaterial color="#14161f" metalness={metal} roughness={0.35}
                            emissive={colour} emissiveIntensity={glow ? 0.22 : 0.06} />
      <Edges color={colour} threshold={20} />
    </RoundedBox>
  );
}

function Fan({ radius = 0.16, colour, position, rotation, spin = 4 }) {
  const blades = useRef();
  useFrame((_, dt) => { if (blades.current) blades.current.rotation.z += dt * spin; });
  return (
    <group position={position} rotation={rotation}>
      <mesh>
        <torusGeometry args={[radius, radius * 0.08, 12, 48]} />
        <meshStandardMaterial color={colour} emissive={colour} emissiveIntensity={1.4} toneMapped={false} />
      </mesh>
      <group ref={blades}>
        {[0, 1, 2, 3, 4, 5, 6].map((i) => (
          <mesh key={i} rotation={[0, 0, (i / 7) * Math.PI * 2]} position={[0, 0, 0]}>
            <boxGeometry args={[radius * 0.28, radius * 1.7, 0.006]} />
            <meshStandardMaterial color="#222634" metalness={0.3} roughness={0.5} transparent opacity={0.85} />
          </mesh>
        ))}
      </group>
    </group>
  );
}

const SHAPES = {
  Motherboard: (c, g) => (
    <group>
      <Block size={[1.3, 1.5, 0.04]} colour={c} glow={g} metal={0.2} />
      {/* chipset heatsinks and slots, for detail */}
      <Block size={[0.5, 0.12, 0.04]} colour={c} glow={g} position={[-0.25, 0.62, 0.04]} />
      <Block size={[0.12, 0.45, 0.04]} colour={c} glow={g} position={[-0.58, 0.45, 0.04]} />
      <Block size={[1.0, 0.03, 0.03]} colour={c} glow={g} position={[-0.05, -0.3, 0.035]} />
    </group>
  ),
  CPU: (c, g) => <Block size={[0.24, 0.24, 0.04]} colour={c} glow={g} metal={0.9} />,
  Cooler: (c, g) => (
    <group>
      <Block size={[0.42, 0.5, 0.36]} colour={c} glow={g} radius={0.03} />
      <Fan colour={c} radius={0.19} position={[0.23, 0, 0]} rotation={[0, Math.PI / 2, 0]} spin={6} />
    </group>
  ),
  RAM: (c, g, part) => (
    <group>
      {Array.from({ length: part.sticks || 2 }).map((_, i) => (
        <Block key={i} size={[0.035, 0.55, 0.13]} colour={c} glow={g} position={[i * 0.07, 0, 0]} />
      ))}
    </group>
  ),
  Storage: (c, g) => <Block size={[0.4, 0.09, 0.02]} colour={c} glow={g} />,
  GPU: (c, g) => (
    <group>
      <Block size={[1.25, 0.16, 0.55]} colour={c} glow={g} radius={0.035} />
      <Fan colour={c} radius={0.15} position={[0.36, -0.09, 0]} rotation={[Math.PI / 2, 0, 0]} />
      <Fan colour={c} radius={0.15} position={[0, -0.09, 0]} rotation={[Math.PI / 2, 0, 0]} />
      <Fan colour={c} radius={0.15} position={[-0.36, -0.09, 0]} rotation={[Math.PI / 2, 0, 0]} />
      {/* light bar on the side you see through the glass */}
      <mesh position={[0, 0, 0.28]}>
        <boxGeometry args={[0.9, 0.025, 0.005]} />
        <meshStandardMaterial color={c} emissive={c} emissiveIntensity={2} toneMapped={false} />
      </mesh>
    </group>
  ),
  PSU: (c, g) => <Block size={[0.75, 0.42, 0.75]} colour={c} glow={g} radius={0.03} />,
};

// The case itself: a glass box with glowing edges and RGB intake fans at the front.
function CaseShell({ part, selected, onSelect }) {
  const [hovered, setHovered] = useState(false);
  const colour = partColour(part, selected, hovered);
  return (
    <group>
      {/* raycast off: clicks go through the glass to the parts inside */}
      <mesh raycast={() => null}>
        <boxGeometry args={[1.9, 2.6, 1.05]} />
        <meshPhysicalMaterial color="#9fdcff" transparent opacity={0.07} roughness={0.05}
                              metalness={0.1} clearcoat={1} depthWrite={false} side={THREE.DoubleSide} />
        <Edges color={colour} />
      </mesh>
      {/* the case is picked by its fans and PSU shroud */}
      <group onClick={(e) => { e.stopPropagation(); onSelect("Case"); }}
             onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = "pointer"; }}
             onPointerOut={() => { setHovered(false); document.body.style.cursor = ""; }}>
      <mesh position={[0, -0.92, 0]}>
        <boxGeometry args={[1.88, 0.02, 1.03]} />
        <meshStandardMaterial color="#0d0f16" metalness={0.5} roughness={0.4} transparent opacity={0.8} />
      </mesh>
      {[0.75, 0.25, -0.25].map((y) => (
        <Fan key={y} colour={NEW_COLOUR} radius={0.2} position={[0.9, y, 0]} rotation={[0, Math.PI / 2, 0]} spin={3} />
      ))}
      <Fan colour={SELECTED_COLOUR} radius={0.18} position={[-0.9, 0.8, -0.1]} rotation={[0, Math.PI / 2, 0]} spin={3} />
      </group>
      {(hovered || selected) && (
        <Html position={[0, 1.45, 0]} center distanceFactor={4.5} zIndexRange={[20, 0]}>
          <div className="rig-tag"><b>Case</b> {part.name}
            <span>{part.condition} · {part.seller} · £{part.price.toFixed(0)}</span></div>
        </Html>
      )}
    </group>
  );
}

function Scene({ parts, selected, animate, onSelect }) {
  const caseShell = parts.find((p) => p.category === "Case");
  const inside = parts.filter((p) => p.category !== "Case" && SHAPES[p.category]);
  return (
    <>
      <ambientLight intensity={0.35} />
      <directionalLight position={[3, 4, 5]} intensity={1.2} />
      <pointLight position={[0, 0.2, 0.3]} intensity={2} color={SELECTED_COLOUR} distance={3} />
      <group rotation={[0, -0.55, 0]}>
        {caseShell && <CaseShell part={caseShell} selected={selected === "Case"} onSelect={onSelect} />}
        {inside.map((part, i) => (
          <Slot key={part.category + part.name} part={part} index={i} animate={animate}
                selected={selected === part.category} onSelect={onSelect}>
            {(colour, glow) => SHAPES[part.category](colour, glow, part)}
          </Slot>
        ))}
      </group>
      <ContactShadows position={[0, -1.35, 0]} opacity={0.5} scale={6} blur={2.5} far={2} />
      <OrbitControls enablePan={false} enableZoom={false} autoRotate={animate} autoRotateSpeed={0.6}
                     minPolarAngle={Math.PI / 3} maxPolarAngle={Math.PI / 1.9} />
    </>
  );
}

export function Build3D({ parts, selected, animate, onSelect }) {
  return (
    <div className="rig-build3d">
      <Canvas camera={{ position: [0, 0.5, 4.6], fov: 40 }} dpr={[1, 2]}
              gl={{ alpha: true, antialias: true }} onPointerMissed={() => onSelect("")}>
        <Scene parts={parts} selected={selected} animate={animate} onSelect={onSelect} />
      </Canvas>
      <div className="rig-legend">
        <span><i style={{ background: NEW_COLOUR }} />New</span>
        <span><i style={{ background: USED_COLOUR }} />Used</span>
        <span className="rig-hint">Drag to turn · click a part</span>
      </div>
    </div>
  );
}
