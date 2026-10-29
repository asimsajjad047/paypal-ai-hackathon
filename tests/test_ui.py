"""The 3D/glass layer: the built bundle must be in the repo and served by Streamlit."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_bundle_is_built_and_served():
    bundle = ROOT / "static" / "rigagent3d.js"
    assert bundle.stat().st_size > 100_000, "run: cd frontend && npm install && npm run build"
    assert "export" in bundle.read_text(encoding="utf-8")[-2000:]   # ES module with mount()
    config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())
    assert config["server"]["enableStaticServing"] is True


def test_part_card_shows_for_clicked_part():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    next(b for b in at.button if b.label.startswith("Build my PC")).click().run()
    at.session_state["focus"] = "GPU"
    at.run()
    assert not at.exception
    gpu = at.session_state.result["build"]["parts"]["GPU"]["Name"]
    assert any(gpu in h.proto.body for h in at.get("html"))
