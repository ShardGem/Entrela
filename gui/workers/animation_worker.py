"""Snapshot worker uses the same engine and configuration contract."""
from dataclasses import replace
from gui.workers.simulation_worker import SimulationWorker
class AnimationWorker(SimulationWorker):
    def __init__(self,config,parent=None):
        super().__init__(replace(config,protocol=replace(config.protocol,save_snapshots=True)),parent)
