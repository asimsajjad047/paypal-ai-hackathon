// The RigAgent "R" in liquid metal, using Paper's LiquidMetal shader
// (@paper-design/shaders-react, Apache-2.0). This is the same shader the
// paper-design/liquid-logo app is built on; that app's own code is not copied
// because its PolyForm Shield licence doesn't fit this MIT repo.
import { LiquidMetal } from "@paper-design/shaders-react";

// A bold geometric "R": the evenodd rule cuts the bowl's hole out of the letter.
const R_MARK = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <path fill="#000" fill-rule="evenodd"
    d="M18 8 H58 A27 27 0 0 1 70 59 L90 92 H63 L46 62 H43 V92 H18 Z
       M43 29 V44 H56 A7.5 7.5 0 0 0 56 29 Z"/>
</svg>`;
const R_MARK_URL = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(R_MARK)}`;

export function Logo({ size, animate }) {
  return (
    <LiquidMetal
      image={R_MARK_URL}
      style={{ width: size, height: size }}
      colorBack="#00000000"
      colorTint="#7fd8ff"
      repetition={2.2}
      softness={0.12}
      shiftRed={0.3}
      shiftBlue={0.3}
      distortion={0.08}
      contour={0.45}
      angle={70}
      scale={0.9}
      fit="contain"
      speed={animate ? 0.8 : 0}
    />
  );
}
