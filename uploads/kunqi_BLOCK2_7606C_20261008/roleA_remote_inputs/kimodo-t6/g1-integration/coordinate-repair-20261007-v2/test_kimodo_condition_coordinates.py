"""Mathematical regression tests; live integration has a separate verifier."""
import importlib
import json
import unittest
from pathlib import Path

import numpy as np


def source_rodrigues(angle, axis):
    """Independent rotation construction for a unit axis."""
    x, y, z = axis
    skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + np.sin(angle) * skew + (1 - np.cos(angle)) * skew @ skew


def source_euler(matrix, axis):
    """Exact extraction equations in upstream _local_rots_to_joint_dofs."""
    return np.dot([
        np.arctan2(matrix[2, 1], matrix[2, 2]),
        np.arctan2(matrix[0, 2], matrix[0, 0]),
        np.arctan2(matrix[1, 0], matrix[1, 1]),
    ], axis)


class CoordinatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).with_name('kimodo_condition_coordinates.py')
        if path.exists():
            cls.repair = importlib.import_module('kimodo_condition_coordinates')
        else:
            cls.repair = None

    def inverse(self, target, offset, principal):
        if self.repair is None:
            # Pre-fix behavior in upstream qpos_to_motion_dict: angle=raw q.
            axis = offset @ principal
            return offset.T @ source_rodrigues(target, axis)
        return self.repair.local_rotation_for_raw_dof(target, offset, principal)

    def test_tilted_axis_recovers_requested_raw_angle(self):
        offset = source_rodrigues(.2, np.array([0., 0., 1.]))
        principal = np.array([1., 0., 0.])
        recovered = source_euler(offset @ self.inverse(.7, offset, principal), offset @ principal)
        self.assertLess(abs(recovered - .7), 1e-6)

    def test_varied_axes_and_angles(self):
        for tilt in [0., .05, .2, -.2]:
            for principal in np.eye(3):
                axis = np.array([1., 2., 3.]); axis /= np.linalg.norm(axis)
                offset = source_rodrigues(tilt, axis)
                for target in [-1.2, -.7, 0., .4, .7, 1.2]:
                    with self.subTest(tilt=tilt, axis=principal.tolist(), target=target):
                        local = self.inverse(target, offset, principal)
                        recovered = source_euler(offset @ local, offset @ principal)
                        self.assertLess(abs(recovered-target), 1e-6)
                        np.testing.assert_allclose(local.T @ local, np.eye(3), atol=1e-12)

    def test_float32_projection_residual(self):
        offset = source_rodrigues(.2, np.array([0., 0., 1.])).astype(np.float32)
        principal = np.array([1., 0., 0.], dtype=np.float32)
        local = self.inverse(.7, offset, principal).astype(np.float32)
        self.assertLess(abs(source_euler(offset @ local, offset @ principal)-.7), 1e-6)

    def test_invalid_inputs_are_rejected(self):
        if self.repair is None:
            self.skipTest('input guards will accompany the repair')
        for target, offset, axis in [
            (np.nan, np.eye(3), [1.,0.,0.]),
            (.7, np.zeros((3,3)), [1.,0.,0.]),
            (.7, np.eye(3), [0.,0.,0.]),
            (.7, np.eye(3), [2.,0.,0.]),
            (100., np.eye(3), [1.,0.,0.]),
        ]:
            with self.assertRaises(ValueError):
                self.repair.local_rotation_for_raw_dof(target, offset, axis)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CoordinatesTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'tests':result.testsRun, 'failures':len(result.failures),
                      'errors':len(result.errors), 'skipped':len(result.skipped),
                      'passed':result.wasSuccessful(), 'scope':'local mathematics only'}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
