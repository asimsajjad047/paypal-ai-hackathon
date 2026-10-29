# Third-party code

`static/rigagent3d.js` is built from `frontend/` and bundles these packages. Their licence
comments are collected in `static/rigagent3d.js.LEGAL.txt`.

| Package | Licence | Used for |
|---|---|---|
| react, react-dom | MIT | Drawing the 3D and logo components |
| three | MIT | 3D engine |
| @react-three/fiber, @react-three/drei | MIT | 3D build view |
| @shadergradient/react | MIT | Animated background |
| @paper-design/shaders, @paper-design/shaders-react | Apache-2.0 | Liquid-metal logo shader |

Apache-2.0 code may be bundled in an MIT project as long as its licence and notices are kept,
which the files above do.

Ideas, not code:

- The glass styling in `static/rigagent.css` is written from scratch, after the look of
  [liquid-glass-js](https://github.com/dashersw/liquid-glass-js) (MIT).
- [liquid-logo](https://github.com/paper-design/liquid-logo) is under the PolyForm Shield
  licence, which doesn't allow relicensing under MIT, so none of its code is copied. The
  logo uses the Apache-2.0 shader package that liquid-logo itself is built on.
