import unittest
from f1energy.event_rl import EventLapEnv
class EventRLTests(unittest.TestCase):
    def test_episode_reward_constraints_and_reset(self):
        env=EventLapEnv();obs,_=env.reset(seed=0);reward=0;done=False
        while not done:
            obs,r,done,truncated,info=env.step([.5]);reward+=r
            self.assertTrue(env.observation_space.contains(obs));self.assertFalse(truncated)
            self.assertGreaterEqual(env.state.energy_j,env.scenario.reserve_j-1e-6)
        self.assertAlmostEqual(-reward,env.state.elapsed_s)
        self.assertAlmostEqual(env.state.speed_m_per_s,20.,places=6)
        with self.assertRaises(RuntimeError):env.step([.5])
    def test_invalid_action(self):
        with self.assertRaises(ValueError):EventLapEnv().step([float('nan')])

    def test_validation_gate_rejects_failed_stale_or_tampered(self):
        import tempfile,json,hashlib
        from pathlib import Path
        from f1energy.event_rl import validate_training_gate
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'src/f1energy').mkdir(parents=True)
            sources={}
            for name in ['event_power_lap.py','power_lap.py']:
                path=root/'src/f1energy'/name;path.write_text('fixture')
                sources[str(path.relative_to(root))]=hashlib.sha256(path.read_bytes()).hexdigest()
            report=root/'summary.json'
            report.write_text(json.dumps({'assessment':{'gate':'passed_synthetic_numerical_gate','physical_checks':True,'analytic':{'passed':True}}}))
            (root/'manifest.json').write_text(json.dumps({'source_hashes':sources,'outputs':{'summary.json':hashlib.sha256(report.read_bytes()).hexdigest()}}))
            validate_training_gate(report,root)
            (root/'src/f1energy/event_power_lap.py').write_text('changed')
            with self.assertRaisesRegex(ValueError,'stale'):validate_training_gate(report,root)
            (root/'src/f1energy/event_power_lap.py').write_text('fixture')
            report.write_text(report.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):validate_training_gate(report,root)
            report.write_text(json.dumps({'assessment':{'gate':'failed'}}))
            with self.assertRaisesRegex(ValueError,'has not passed'):validate_training_gate(report,root)
