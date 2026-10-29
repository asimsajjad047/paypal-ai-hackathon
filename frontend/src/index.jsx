// RigAgent's visual layer. Streamlit loads this file once (from /app/static/rigagent3d.js)
// and calls mount(kind, component) for each st.components.v2 component in ui.py.
//
// component = { data, parentElement, setTriggerValue, ... } from Streamlit.
// Streamlit calls mount() again on every rerun, so each React root is kept and
// re-rendered with the new data instead of being rebuilt (no flicker, no lost camera).
import { createRoot } from "react-dom/client";
import { Background } from "./Background.jsx";
import { Build3D } from "./Build3D.jsx";
import { Logo } from "./Logo.jsx";

const roots = new Map();          // one React root per (kind, key)
const pendingUnmount = new Map();

function rootFor(id, makeHost) {
  clearTimeout(pendingUnmount.get(id));
  pendingUnmount.delete(id);
  let entry = roots.get(id);
  if (!entry || !entry.host.isConnected) {
    entry?.root.unmount();
    const host = makeHost();
    entry = { host, root: createRoot(host) };
    roots.set(id, entry);
  }
  return entry;
}

// Streamlit runs the returned cleanup before each re-mount. Waiting a moment
// means a plain rerun (which mounts again straight away) keeps the same scene.
function laterUnmount(id) {
  return () => {
    pendingUnmount.set(id, setTimeout(() => {
      roots.get(id)?.root.unmount();
      roots.get(id)?.host.remove();
      roots.delete(id);
    }, 1500));
  };
}

function hostIn(parent, className) {
  return () => {
    const div = document.createElement("div");
    div.className = className;
    parent.appendChild(div);
    return div;
  };
}

// Liquid-glass buttons: tell the CSS where the pointer is, so the shine follows it.
document.addEventListener("pointermove", (e) => {
  const button = e.target.closest?.(".stButton > button, .stFormSubmitButton > button, .stLinkButton > a");
  if (!button) return;
  const box = button.getBoundingClientRect();
  button.style.setProperty("--mx", `${e.clientX - box.left}px`);
  button.style.setProperty("--my", `${e.clientY - box.top}px`);
}, { passive: true });

export function mount(kind, component) {
  const { data = {}, parentElement, setTriggerValue } = component;

  if (kind === "background") {
    // The gradient lives on <body>, behind the whole app, and is never unmounted.
    const { root, host } = rootFor("background", () => {
      const div = document.createElement("div");
      div.id = "rig-bg";
      document.body.prepend(div);
      return div;
    });
    host.style.display = data.enabled ? "block" : "none";
    if (data.enabled) root.render(<Background calm={data.calm} />);
    return undefined;
  }

  const id = `${kind}:${data.key || ""}`;
  const { root } = rootFor(id, hostIn(parentElement, `rig-${kind}`));
  if (kind === "logo") {
    root.render(<Logo size={data.size || 64} animate={data.animate !== false} />);
  } else if (kind === "build3d") {
    root.render(<Build3D parts={data.parts || []} selected={data.selected}
                         animate={data.animate !== false}
                         onSelect={(cat) => setTriggerValue("selected", cat)} />);
  }
  return laterUnmount(id);
}
