"""Local human-vs-agent teaching GUI."""

from arena.gui.controller import KuhnGuiController
from arena.gui.human_agent import HumanActionProvider, HumanAgent
from arena.gui.server import serve_gui

__all__ = ["HumanActionProvider", "HumanAgent", "KuhnGuiController", "serve_gui"]
