"""
Speculum Principis - A Python-based generative agent for monitoring public internet material.

This package provides tools for discovering and analyzing new/evolving study subjects
from various internet sources including news feeds, social media, and academic publications.
"""

__version__ = "0.1.0"
__author__ = "Terrence Giggy"
__email__ = "terrence@example.com"

from .agent.core import SpeculumAgent
from .monitoring.sources import SourceManager
from .analysis.processor import ContentProcessor

__all__ = ["SpeculumAgent", "SourceManager", "ContentProcessor"]