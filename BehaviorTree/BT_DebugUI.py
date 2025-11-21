from typing import Tuple

def _ui_text_colored(text: str, color: Tuple[float, float, float, float]) -> None:
    # Pylance doesn't know the real PyImGui signature, so ignore its type here.
    PyImGui.text_colored(text, color)  # type: ignore[call-arg]

def _ui_push_style_color(idx: int, color: Tuple[float, float, float, float]) -> None:
    PyImGui.push_style_color(idx, color)  # type: ignore[call-arg]

def _ui_pop_style_color(count: int = 1) -> None:
    PyImGui.pop_style_color(count)  # type: ignore[call-arg]
import PyImGui
from BehaviorTree.BehaviorTree import BT_ROOT, NodeState
from Py4GWCoreLib.py4gwcorelib_src.Color import Color

STATE_PREFIX = {
    NodeState.RUNNING: "[▶] ",
    NodeState.SUCCESS: "[✓] ",
    NodeState.FAILURE: "[✗] ",
    None: "[ ] ",
}

from typing import Optional

STATE_COLORS: dict[Optional[NodeState], tuple[float, float, float, float]] = {
    NodeState.RUNNING: Color(255, 215, 0).to_rgba(),    # gold
    NodeState.SUCCESS: Color(0, 200, 0).to_rgba(),      # green
    NodeState.FAILURE: Color(220, 20, 60).to_rgba(),    # red
    None: Color(128, 128, 128).to_rgba(),               # gray
}

def _node_label(node) -> str:
    state = getattr(node, "last_state", None)
    prefix = STATE_PREFIX.get(state, "[ ] ")
    node_type = getattr(node, "node_type", node.__class__.__name__)
    name = getattr(node, "name", node_type)
    dur = getattr(node, "last_duration_ms", 0.0)
    return f"{prefix}[{node_type}] {name} ({dur:.1f}ms)"

def draw_node(node):
    if node is None:
        return

    label = _node_label(node)
    state = getattr(node, "last_state", None)
    state_color = STATE_COLORS.get(state, STATE_COLORS[None])

    # Leaf nodes
    if not hasattr(node, "children"):
        _ui_text_colored(label, state_color)
        dur = getattr(node, "last_duration_ms", 0.0)
        acc = getattr(node, "accumulated_ms", 0.0)
        PyImGui.text(f"    State: {state}  Last: {dur:.1f} ms  Acc: {acc:.1f} ms")
        return

    # Composite nodes
    _ui_push_style_color(0, state_color)
    open_ = PyImGui.tree_node(label)
    _ui_pop_style_color()

    dur = getattr(node, "last_duration_ms", 0.0)
    acc = getattr(node, "accumulated_ms", 0.0)
    PyImGui.text(f"    State: {state}  Last: {dur:.1f} ms  Acc: {acc:.1f} ms")

    if open_:
        for child in getattr(node, "children", []):
            draw_node(child)
        PyImGui.tree_pop()

def draw_bt_debugger_ui(root=None):
    if root is None:
        root = BT_ROOT
    if root is None:
        return

    PyImGui.set_next_window_size(450, 600)
    if not PyImGui.begin("Behavior Tree Debugger", True):
        PyImGui.end()
        return

    draw_node(root)
    PyImGui.end()
