// Animated full-screen gradient, made with ShaderGradient (MIT, github.com/ruucm/shadergradient).
// lightType "3d" uses plain lights, so nothing is downloaded at runtime (the "env" lights fetch HDR files).
import { ShaderGradient, ShaderGradientCanvas } from "@shadergradient/react";

export function Background({ calm }) {
  return (
    <ShaderGradientCanvas pointerEvents="none" pixelDensity={1} fov={45} lazyLoad={false}
                          style={{ position: "absolute", inset: 0 }}>
      <ShaderGradient
        control="props"
        type="waterPlane"
        animate={calm ? "off" : "on"}
        uSpeed={0.12}
        uStrength={1.4}
        uDensity={1.3}
        uFrequency={5.5}
        uAmplitude={0}
        positionX={0} positionY={0} positionZ={0}
        rotationX={50} rotationY={0} rotationZ={-60}
        color1="#3a22c9"
        color2="#0c74b8"
        color3="#06051a"
        reflection={0.1}
        brightness={0.85}
        lightType="3d"
        grain="off"
        cAzimuthAngle={180}
        cPolarAngle={80}
        cDistance={2.8}
        cameraZoom={9.1}
      />
    </ShaderGradientCanvas>
  );
}
