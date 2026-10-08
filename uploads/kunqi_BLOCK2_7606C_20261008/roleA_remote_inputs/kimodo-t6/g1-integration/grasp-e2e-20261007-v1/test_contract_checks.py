"""Regression checks for export provenance, coverage and continuous hold."""
import tempfile
from pathlib import Path
import unittest
import numpy as np
from export_kimodo_reference import resample,frame_zero_report,verify_generation
from grasp_metrics import HoldTimer

class ContractTests(unittest.TestCase):
    def test_no_source_padding(self):
        q=np.zeros((487,36));q[:,3]=1;t=np.arange(810)/50
        self.assertEqual(resample(q,30,t).shape,(810,36))
        with self.assertRaises(ValueError):resample(q[:486],30,t)
        q[3,7]=np.nan
        with self.assertRaises(ValueError):resample(q,30,t)
    def test_noncanonical_start_rejected(self):
        q=np.zeros((810,36));q[:,3]=1;initial=q[0].copy();q[0,7]=.01
        self.assertFalse(frame_zero_report(q,initial,np.zeros((810,14)))['pass'])
    def test_dry_run_and_fixture_not_actual_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for gen in ({'model_generation_run':False},{'model_generation_run':True,'model_name':'ARDY'}):
                with self.assertRaises(ValueError):verify_generation(p,p,{'task_id':'test'},gen)
    def test_hold_resets_on_any_invalid_step(self):
        timer=HoldTimer()
        for _ in range(300):timer.update(True,.005)
        self.assertAlmostEqual(timer.current,1.5)
        timer.update(False,.005);self.assertEqual(timer.current,0)
        for _ in range(400):timer.update(True,.005)
        self.assertAlmostEqual(timer.maximum,2.)
        timer.update(False,.005);self.assertEqual(timer.current,0);self.assertAlmostEqual(timer.maximum,2.)
if __name__=='__main__':unittest.main()
