
import PyImGui
from BehaviorTree.BehaviorTree import NodeState

from Py4GWCoreLib.ImGui_src.IconsFontAwesome5 import IconsFontAwesome5

# ImGui text color index (ImGuiCol.Text = 0)
TEXT_COLOR_IDX = 0

STATE_COLORS = {
    None:              (0.80, 0.80, 0.80, 1.0),  # not run yet
    NodeState.SUCCESS: (0.20, 0.85, 0.20, 1.0),  # green
    NodeState.FAILURE: (0.90, 0.25, 0.25, 1.0),  # red
    NodeState.RUNNING: (0.25, 0.55, 1.00, 1.0),  # blue for running
}

NODETYPE_COLORS = {
    "Selector":   (0.25, 0.70, 1.00, 1.0),
    "Sequence":   (0.25, 0.70, 1.00, 1.0),
    "Condition":  (0.20, 0.85, 0.20, 1.0),
    "Action":     (1.00, 0.65, 0.00, 1.0),
    "Subtree":    (0.65, 0.45, 1.00, 1.0),
}

DEFAULT_COLOR = (0.80, 0.80, 0.80, 1.0)



# =============================
#  LABEL BUILDER
# =============================
def _node_label(node):
    node_type = getattr(node, "node_type", "Node")
    name = getattr(node, "name", "<?>")
    state = getattr(node, "last_state", None)
    last_ms = getattr(node, "last_duration_ms", 0.0) or 0.0
    accum_ms = getattr(node, "accumulated_ms", 0.0) or 0.0

    if state == NodeState.SUCCESS:
        state_str = "SUCCESS"
    elif state == NodeState.FAILURE:
        state_str = "FAILURE"
    elif state == NodeState.RUNNING:
        state_str = "RUNNING"
    else:
        state_str = "NONE"

    # Icon mapping
    if node_type == "Selector":
        icon = IconsFontAwesome5.ICON_CODE_BRANCH
    elif node_type == "Sequence":
        icon = IconsFontAwesome5.ICON_STREAM
    elif node_type == "Condition":
        icon = IconsFontAwesome5.ICON_QUESTION_CIRCLE
    elif node_type == "Action":
        icon = IconsFontAwesome5.ICON_BOLT
    elif node_type == "Subtree":
        icon = IconsFontAwesome5.ICON_PROJECT_DIAGRAM
    else:
        icon = ""

    label = f"{icon} [{node_type}] {name} | {state_str} [{last_ms:.3f}ms / {accum_ms:.3f}ms]"
    type_color = NODETYPE_COLORS.get(node_type, DEFAULT_COLOR)
    return label, type_color, state_str, last_ms, accum_ms


# =============================
#  NODE DRAWING
# =============================

def _ui_push_style_color(color):
    PyImGui.push_style_color(TEXT_COLOR_IDX, color)


def _ui_pop_style_color():
    PyImGui.pop_style_color(1)


def draw_node(node):
    if node is None:
        return

    label, type_color, state_str, last_ms, accum_ms = _node_label(node)
    state = getattr(node, "last_state", None)
    state_color = STATE_COLORS.get(state, DEFAULT_COLOR)
    children = getattr(node, "children", None)
    has_children = bool(children)

    # For nodes with children: the label itself is the tree header
    if has_children:
        if type_color is not None:
            _ui_push_style_color(type_color)
        opened = PyImGui.tree_node(label)
        if type_color is not None:
            _ui_pop_style_color()
    else:
        # Leaf nodes: no arrow, just colored label
        if type_color is not None:
            PyImGui.text_colored(label, type_color)
        else:
            PyImGui.text(label)
        opened = True  # still show details below

    if opened:
        # Details (match the style of the reference screenshot)
        PyImGui.text_colored(f"State: {state_str}", state_color)
        PyImGui.text(f"Last Duration: {last_ms:.3f} ms")
        PyImGui.text(f"Accumulated:  {accum_ms:.3f} ms")
        PyImGui.separator()

        # Draw children inside the same tree node
        if has_children:
            for child in children:
                draw_node(child)
            PyImGui.tree_pop()


# =============================
#  MAIN WINDOW
# =============================

def draw_bt_debugger_ui(root=None):
    if root is None:
        return

    PyImGui.set_next_window_size(450, 650)
    if PyImGui.begin("Behavior Tree Debugger", True):
        draw_node(root)
    PyImGui.end()
