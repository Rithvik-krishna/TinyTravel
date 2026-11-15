"""
Playbooks for deterministic, own-agent hotel checkout automation.
"""
from .cleartrip import run_cleartrip_playbook
from .agoda import run_agoda_playbook

__all__ = ["run_cleartrip_playbook", "run_agoda_playbook"]
