"""Candidate canonical condition inverse; preserves the existing Kimodo exporter.

Only raw-DOF, wxyz single clips are supported. No runtime monkeypatches, clamping,
neutral-frame overwrites, controller changes, or upstream edits are performed.
Live Kimodo/canonical verification must pass before this is used for generation.
"""
from __future__ import annotations

import numpy as np


def _rotation(angle: float, axis: np.ndarray) -> np.ndarray:
    unit = axis / np.linalg.norm(axis)
    x, y, z = unit
    skew = np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])
    return np.eye(3) + np.sin(angle)*skew + (1-np.cos(angle))*(skew @ skew)


def _euler_projection(matrix: np.ndarray, axis: np.ndarray) -> float:
    components = [np.arctan2(matrix[2,1], matrix[2,2]),
                  np.arctan2(matrix[0,2], matrix[0,0]),
                  np.arctan2(matrix[1,0], matrix[1,1])]
    return float(np.dot(components, axis))


def local_rotation_for_raw_dof(target: float, offset, principal_axis) -> np.ndarray:
    """Invert the current converter's Euler projection on its hinge family.

The axis-angle parameter is not generally the exported raw joint angle. Solve
for it near the requested angle, then require a tight forward residual. Reject
singular, discontinuous or distant solutions rather than silently substituting
a pose. A +/-0.25rad branch neighborhood is a solver guard, not a joint limit.
"""
    offset = np.asarray(offset, dtype=np.float64)
    principal = np.asarray(principal_axis, dtype=np.float64)
    if (not np.isfinite(target) or offset.shape != (3,3) or principal.shape != (3,)
            or not np.all(np.isfinite(offset)) or not np.all(np.isfinite(principal))):
        raise ValueError('Expected finite target, rotation offset and unit hinge axis')
    if (not np.allclose(offset.T @ offset, np.eye(3), atol=1e-6, rtol=0)
            or abs(np.linalg.det(offset)-1) > 1e-6
            or abs(np.linalg.norm(principal)-1) > 1e-6):
        raise ValueError('Offset must be a proper rotation and axis must be unit length')
    axis = offset @ principal

    def evaluate(parameter):
        local = offset.T @ _rotation(parameter, axis)
        # Include numerical offset*offset.T to match the actual forward path.
        return _euler_projection(offset @ local, axis), local

    parameter = float(target)
    for _ in range(32):
        value, local = evaluate(parameter)
        residual = value - target
        if abs(residual) < 1e-11:
            return local
        h = 1e-6
        slope = (evaluate(parameter+h)[0]-evaluate(parameter-h)[0])/(2*h)
        if not np.isfinite(slope) or abs(slope) < 1e-5:
            break
        step = float(np.clip(residual/slope, -.05, .05))
        candidate = parameter-step
        if abs(candidate-target) > .25:
            break
        # Backtracking prevents Newton steps crossing a projection discontinuity.
        accepted = False
        for _ in range(12):
            if abs(evaluate(candidate)[0]-target) < abs(residual):
                accepted = True
                break
            step *= .5
            candidate = parameter-step
        if not accepted:
            break
        parameter = candidate
    raise ValueError(f'Cannot invert raw DOF {target:g} on a continuous nearby branch')


def qpos_to_motion_dict_exact(converter, qpos, source_fps: float):
    """Build a motion dict and verify it using the unchanged live to_qpos().

Input (T,36): root xyz, quaternion wxyz, 29 hinges in converter XML order.
Use at least 8 frames because upstream root smoothing rejects very short clips.
This wrapper is CPU/float32; the nonlinear scalar inverse uses float64 internally.
"""
    import torch
    from kimodo.exports.motion_io import complete_motion_dict

    q = np.asarray(qpos, dtype=np.float32)
    if q.ndim != 2 or q.shape[1] != 36 or q.shape[0] < 8:
        raise ValueError('Expected a single (T>=8,36) qpos clip')
    if not np.all(np.isfinite(q)) or not np.isfinite(source_fps) or source_fps <= 0:
        raise ValueError('qpos and FPS must be finite; FPS must be positive')
    if not np.allclose(np.linalg.norm(q[:,3:7], axis=-1), 1., atol=1e-6, rtol=0):
        raise ValueError('Input root quaternion must have unit norm')
    base = converter.qpos_to_motion_dict(
        q, source_fps=source_fps, root_quat_w_first=True, mujoco_rest_zero=False)
    local = base['local_rot_mats'].clone()
    offsets = converter._rot_offsets_f2q.detach().cpu().numpy()
    axes = converter._mujoco_joint_axis_values_kimodo_space.detach().cpu().numpy()
    mapping = converter._mujoco_indices_to_kimodo_indices.detach().cpu().numpy()
    for hinge, joint in enumerate(mapping):
        # Repeated angles are common in sparse/neutral task condition clips.
        values, indices = np.unique(q[:,7+hinge], return_inverse=True)
        matrices = np.stack([local_rotation_for_raw_dof(float(value), offsets[joint], axes[hinge])
                             for value in values])
        local[:,int(joint)] = torch.as_tensor(matrices[indices], dtype=local.dtype, device=local.device)
    motion = complete_motion_dict(local, base['root_positions'], converter.skeleton, source_fps)
    for name, value in motion.items():
        if isinstance(value, torch.Tensor) and not torch.isfinite(value).all().item():
            raise ValueError(f'Non-finite derived motion field: {name}')
    recovered = converter.to_qpos(
        motion['local_rot_mats'][None], motion['root_positions'][None],
        root_quat_w_first=True, mujoco_rest_zero=False).detach().cpu().numpy()[0]
    if not np.all(np.isfinite(recovered)):
        raise ValueError('Forward converter returned non-finite qpos')
    # Quaternions q and -q represent the same orientation.
    recovered = recovered.copy()
    signs = np.where(np.sum(recovered[:,3:7]*q[:,3:7], axis=-1) < 0., -1., 1.)
    recovered[:,3:7] *= signs[:,None]
    error = float(np.max(np.abs(recovered-q)))
    if error > 1e-6:
        raise ValueError(f'Unchanged forward converter roundtrip failed: max error={error:g}')
    return motion
