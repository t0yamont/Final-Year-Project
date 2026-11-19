import hashlib,json,tempfile,unittest
from pathlib import Path
from f1energy.circuit_training_gate import validate_control_gate


class TrainingGateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.write('reference.json',{'mass':800})
        names=['src/f1energy/circuit.py','src/f1energy/event_power_lap.py','src/f1energy/power_lap.py']
        for name in names:self.write(name,{'version':1})
        self.sources={str(Path(n)):self.sha(n) for n in names}
        self.write('numerical/metrics.json',{'all_numerical_gates_passed':True})
        self.write('numerical/manifest.json',dict(inputs={'reference.json':self.sha('reference.json')},sources=self.sources,
            outputs={'numerical/metrics.json':self.sha('numerical/metrics.json')}))
        self.write('baseline/contract.json',{'config':{'numerical_gate':'numerical'}})
        self.write('baseline/metrics.json',{'pilot_gate_passed':True})
        self.write('baseline/manifest.json',dict(inputs={'numerical/manifest.json':self.sha('numerical/manifest.json')},sources=self.sources,
            outputs={n:self.sha(n) for n in ['baseline/contract.json','baseline/metrics.json']}))
    def write(self,name,obj):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj))
    def sha(self,name):return hashlib.sha256((self.root/name).read_bytes()).hexdigest()
    def test_valid_evidence(self):self.assertTrue(validate_control_gate('baseline',self.root)[1]['pilot_gate_passed'])
    def test_nested_reference_change_rejected(self):
        self.write('reference.json',{'mass':900})
        with self.assertRaisesRegex(ValueError,'reference.json'):validate_control_gate('baseline',self.root)
    def test_changed_solver_rejected(self):
        self.write('src/f1energy/circuit.py',{'version':2})
        with self.assertRaises(ValueError):validate_control_gate('baseline',self.root)
    def test_corrupt_report_rejected(self):
        self.write('baseline/metrics.json',{'pilot_gate_passed':False})
        with self.assertRaises(ValueError):validate_control_gate('baseline',self.root)
