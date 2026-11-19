"""Reject stale numerical and controller evidence before circuit training."""
import hashlib,json
from pathlib import Path


def validate_control_gate(baseline_dir, project_root):
    root=Path(project_root);baseline=root/baseline_dir
    def verify(folder,groups):
        manifest=json.loads((folder/'manifest.json').read_text())
        for group in groups:
            if not manifest.get(group):raise ValueError('missing evidence hashes: '+group)
            for name,expected in manifest[group].items():
                p=root/name
                if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
                    raise ValueError('stale or corrupt evidence: '+name)
        metrics_path=folder/'metrics.json'
        normalized={str((root/k).resolve()):v for k,v in manifest['outputs'].items()}
        if str(metrics_path.resolve()) not in normalized:raise ValueError('metrics are not hash-bound')
        return json.loads(metrics_path.read_text())
    report=verify(baseline,['inputs','sources','outputs'])
    if not report.get('pilot_gate_passed'):raise ValueError('controller gate failed')
    contract=json.loads((baseline/'contract.json').read_text())
    config=contract['config']
    # The numerical runner's own file can evolve; the physical sources must match.
    numerical=root/config['numerical_gate']
    numerical_manifest=json.loads((numerical/'manifest.json').read_text())
    for name in ['src/f1energy/circuit.py','src/f1energy/event_power_lap.py','src/f1energy/power_lap.py']:
        expected=numerical_manifest['sources'].get(str(Path(name)))
        if expected!=hashlib.sha256((root/name).read_bytes()).hexdigest():raise ValueError('stale numerical physics')
    numerical_report=verify(numerical,['inputs','outputs'])
    if not numerical_report.get('all_numerical_gates_passed'):raise ValueError('numerical gate failed')
    return config,report
