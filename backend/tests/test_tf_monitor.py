"""Test del monitor TF (senza ROS, via injection diretta)."""

from __future__ import annotations

from app.services.tf_monitor import TfMonitor


def test_tree_unavailable_when_inactive() -> None:
    """Senza trasformate e monitor inattivo l'albero e' non disponibile."""
    tree = TfMonitor().get_tree()
    assert tree.available is False
    assert tree.frames == []


def test_single_root_tree() -> None:
    """Una catena di frame deve avere una sola radice (il genitore in cima)."""
    monitor = TfMonitor()
    monitor.update_transform("base_link", "odom", is_static=False)
    monitor.update_transform("laser", "base_link", is_static=True)
    tree = monitor.get_tree()
    assert tree.available is True
    assert tree.roots == ["odom"]
    by_id = {f.frame_id: f for f in tree.frames}
    assert by_id["base_link"].parent == "odom"
    assert by_id["laser"].is_static is True
    assert by_id["odom"].parent is None


def test_disconnected_trees_have_multiple_roots() -> None:
    """Due catene scollegate devono produrre piu' di una radice."""
    monitor = TfMonitor()
    monitor.update_transform("base_link", "odom", is_static=False)
    monitor.update_transform("tool", "arm", is_static=False)
    tree = monitor.get_tree()
    assert tree.roots == ["arm", "odom"]
    assert len(tree.roots) > 1
