"""Synthetic event-based power/drag/braking environment; training requires validation."""
from dataclasses import dataclass,asdict
import numpy as np
import gymnasium as gym
from .power_lap import PowerVehicle,PowerState
from .event_power_lap import integrate_segment

@dataclass(frozen=True)
class EventScenario:
    lengths_m: tuple=(400.,400.)
    exit_caps_m_per_s: tuple=(30.,20.)
    initial_speed_m_per_s: float=20.
    initial_energy_j: float=450000.
    reserve_j: float=50000.
    vehicle: PowerVehicle=PowerVehicle()

class EventLapEnv(gym.Env):
    metadata={'render_modes':[]}
    def __init__(self,scenario=None):
        self.scenario=scenario or EventScenario()
        self.action_space=gym.spaces.Box(0.,1.,(1,),dtype=np.float32)
        self.observation_space=gym.spaces.Box(0.,np.inf,(3,),dtype=np.float32)
        self.reset()
    def _obs(self):
        return np.array([self.index/len(self.scenario.lengths_m),self.state.speed_m_per_s/100.,
          max(0.,self.state.energy_j-self.scenario.reserve_j)/max(1.,self.scenario.initial_energy_j-self.scenario.reserve_j)],dtype=np.float32)
    def reset(self,*,seed=None,options=None):
        super().reset(seed=seed);self.index=0;self.state=PowerState(self.scenario.initial_speed_m_per_s,self.scenario.initial_energy_j)
        return self._obs(),{}
    def step(self,action):
        a=np.asarray(action)
        if self.index>=len(self.scenario.lengths_m):raise RuntimeError('reset required')
        if a.shape!=(1,) or not np.isfinite(a).all() or not 0<=float(a[0])<=1:raise ValueError('action fraction invalid')
        s=self.scenario
        self.state,info=integrate_segment(s.vehicle,self.state,s.lengths_m[self.index],s.exit_caps_m_per_s[self.index],float(a[0]),reserve_j=s.reserve_j)
        self.index+=1
        return self._obs(),-info['duration_s'],self.index==len(s.lengths_m),False,info

def validate_training_gate(report_path, project_root):
    """Require passing numerical evidence tied to the current solver sources."""
    import hashlib,json
    from pathlib import Path
    report_path=Path(report_path);root=Path(project_root)
    report=json.loads(report_path.read_text(encoding='utf-8-sig'))
    assessment=report.get('assessment',{})
    if assessment.get('gate')!='passed_synthetic_numerical_gate' or assessment.get('physical_checks') is not True or assessment.get('analytic',{}).get('passed') is not True:
        raise ValueError('numerical/physical/analytic validation gate has not passed')
    manifest=json.loads((report_path.parent/'manifest.json').read_text(encoding='utf-8-sig'))
    outputs=manifest.get('outputs',{})
    if outputs.get(report_path.name)!=hashlib.sha256(report_path.read_bytes()).hexdigest():
        raise ValueError('validation report hash mismatch')
    sources={key.replace('\\','/'):value for key,value in manifest.get('source_hashes',{}).items()}
    for relative in ['src/f1energy/event_power_lap.py','src/f1energy/power_lap.py']:
        path=root/relative
        if not path.is_file() or sources.get(relative)!=hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('validation is stale or does not identify current solver: '+relative)
    return manifest
