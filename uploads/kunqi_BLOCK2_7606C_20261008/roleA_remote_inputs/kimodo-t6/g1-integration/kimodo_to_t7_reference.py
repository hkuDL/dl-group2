#!/usr/bin/env python3
"""Phase 1 only: Kimodo NPZ to a validated T7 body/root intermediate.

Activate g1-integration/activate-g1.sh before calling this module or its CLI.
No hand trajectories, replay, load_reference(), projection or clamping are used.
An existing output directory is never reused, including an empty directory.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

BASE = Path('/workspace/group2/kimodo-t6/g1-integration')
CANONICAL = Path('/workspace/group2/dl-group2/scripts/expert_trajectory.py')
WIDTHS = {'body_ref_q': 29, 'body_ref_dq': 29, 'root_ref_pos': 3,
          'root_ref_quat': 4, 'root_lin_vel': 3, 'root_ang_vel': 3}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def joint_permutation(source_names, canonical_names):
    require(len(source_names) == len(set(source_names)), 'Duplicate Kimodo joint names')
    require(len(canonical_names) == len(set(canonical_names)), 'Duplicate canonical joint names')
    require(set(source_names) == set(canonical_names),
            f'Joint sets disagree: missing={set(canonical_names)-set(source_names)}, '
            f'extra={set(source_names)-set(canonical_names)}')
    kimodo_joint_name_to_index = {name: i for i, name in enumerate(source_names)}
    canonical_body_joint_name_to_index = {name: i for i, name in enumerate(canonical_names)}
    permutation = [kimodo_joint_name_to_index[name] for name, _ in
                   sorted(canonical_body_joint_name_to_index.items(), key=lambda item: item[1])]
    require(sorted(permutation) == list(range(len(source_names))), 'Incomplete permutation')
    return permutation


def target_timestamps(source_t, target_fps):
    require(np.isfinite(target_fps) and target_fps > 0, 'FPS must be finite and positive')
    require(source_t.ndim == 1 and len(source_t) >= 2 and np.isfinite(source_t).all()
            and source_t[0] == 0 and np.all(np.diff(source_t) > 0), 'Invalid source timestamps')
    # Include grid points inside the source interval only, even at floating boundaries.
    target_t = np.arange(int(np.floor(source_t[-1] * target_fps)) + 2, dtype=np.float64) / target_fps
    target_t = target_t[target_t <= source_t[-1]]
    require(len(target_t) >= 3, 'At least three target frames are required for derivatives')
    return target_t


def checked_quaternions(q):
    q = np.asarray(q, dtype=np.float64).copy()
    require(q.ndim == 2 and q.shape[1] == 4 and np.isfinite(q).all(), 'Invalid quaternion array')
    norms = np.linalg.norm(q, axis=1)
    require(np.allclose(norms, 1, rtol=0, atol=1e-5), 'Quaternions must already be unit wxyz')
    q /= norms[:, None]  # Remove converter float32 roundoff only.
    for i in range(1, len(q)):
        if np.dot(q[i-1], q[i]) < 0:
            q[i] *= -1
    return q


def resample_quaternions(source_t, source_q, target_t):
    q = checked_quaternions(source_q)
    require(len(q) == len(source_t), 'Quaternion/timestamp lengths disagree')
    require(np.isfinite(target_t).all() and target_t.min() >= source_t[0]
            and target_t.max() <= source_t[-1], 'Quaternion extrapolation is prohibited')
    # SciPy xyzw is confined to this boundary; all adapter arrays are wxyz.
    result = Slerp(source_t, Rotation.from_quat(q[:, [1, 2, 3, 0]]))(target_t)
    return checked_quaternions(result.as_quat()[:, [3, 0, 1, 2]])


def world_angular_velocity(q, timestamps):
    q = checked_quaternions(q)
    dt = np.diff(timestamps)
    require(len(q) == len(timestamps) and len(q) >= 2 and np.isfinite(dt).all()
            and np.all(dt > 0), 'Invalid angular velocity timestamps')
    rotations = Rotation.from_quat(q[:, [1, 2, 3, 0]])
    # Left multiplication: q_next * inverse(q_current), expressed in world axes.
    interval = (rotations[1:] * rotations[:-1].inv()).as_rotvec() / dt[:, None]
    result = np.empty((len(q), 3), dtype=np.float64)
    result[0], result[-1] = interval[0], interval[-1]
    result[1:-1] = (interval[:-1] + interval[1:]) / 2
    return result


def canonical_order(path):
    path = Path(path).resolve(strict=True)
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location('_phase1_canonical_expert', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        body, _, _ = module.orders()  # Never call load_reference on this intermediate.
        require(len(body) == len(set(body)) == 29, 'Canonical body must contain 29 unique names')
        return list(body), module.SONIC_REPO
    finally:
        sys.path.pop(0)


def load_motion(path):
    shapes = {'local_rot_mats': (34, 3, 3), 'global_rot_mats': (34, 3, 3),
              'posed_joints': (34, 3), 'root_positions': (3,), 'smooth_root_pos': (3,),
              'foot_contacts': (4,), 'global_root_heading': (2,)}
    with np.load(path, allow_pickle=False) as z:
        require(set(shapes).issubset(z.files), f'Missing NPZ keys: {set(shapes)-set(z.files)}')
        data = {key: z[key].copy() for key in shapes}
    frames = len(data['root_positions'])
    require(frames >= 2, 'Motion needs at least two source frames')
    for key, shape in shapes.items():
        require(data[key].shape == (frames,) + shape, f'Invalid shape for {key}: {data[key].shape}')
        require(np.isfinite(data[key]).all(), f'Nonfinite source values in {key}')
    for key in ('local_rot_mats', 'global_rot_mats'):
        r = data[key]
        require(np.allclose(r @ r.swapaxes(-1, -2), np.eye(3), rtol=0, atol=1e-4)
                and np.allclose(np.linalg.det(r), 1, rtol=0, atol=1e-4),
                f'Invalid rotation matrices in {key}')
    return data


def validate_arrays(arrays, body_order, metadata):
    t = arrays['timestamps']
    require(t.ndim == 1 and len(t) >= 3 and np.isfinite(t).all(), 'Invalid target timestamps')
    require(t[0] == 0 and np.all(np.diff(t) > 0)
            and np.allclose(np.diff(t), .02, rtol=0, atol=1e-12), 'Expected strictly increasing 50 Hz timestamps')
    require(t[-1] <= metadata['source_end_time'], 'Target extrapolation')
    for key, width in WIDTHS.items():
        require(arrays[key].shape == (len(t), width) and np.isfinite(arrays[key]).all(), f'Invalid {key}')
    norms = np.linalg.norm(arrays['root_ref_quat'], axis=1)
    require(np.allclose(norms, 1, rtol=0, atol=1e-10), 'Invalid output quaternion norms')
    require(metadata['body_joint_order'] == body_order, 'Body order differs from canonical orders()')
    require(sorted(metadata['joint_permutation']) == list(range(29)), 'Invalid mapping')
    require(set(arrays) == set(WIDTHS) | {'timestamps'}, 'Unexpected arrays, including hand arrays')
    return {'shapes': {k: list(v.shape) for k, v in arrays.items()},
            'timestamp_range': [float(t[0]), float(t[-1])], 'target_dt': .02,
            'quaternion_norm_min': float(norms.min()), 'quaternion_norm_max': float(norms.max()),
            'finite_values': 'PASS', 'joint_order_and_permutation': 'PASS', 'no_hand_arrays': 'PASS'}


def write_output(output, arrays, metadata):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, value in arrays.items():
        with (output / f'{name}.npy').open('xb') as f:
            np.save(f, value, allow_pickle=False)
    with (output / 'metadata.json').open('x') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def convert(input_path, output_path, source_fps=30., target_fps=50., canonical_path=CANONICAL):
    # Suppress bytecode writes when reading protected upstream modules.
    sys.dont_write_bytecode = True
    require(np.isfinite(source_fps) and source_fps > 0, 'Source FPS must be finite and positive')
    require(target_fps == 50., 'Canonical Phase 1 target FPS is fixed at 50')
    input_path = Path(input_path).resolve(strict=True)
    output_path = Path(output_path).absolute()
    if output_path.exists():
        raise FileExistsError(f'Refusing to overwrite existing output: {output_path}')
    import torch
    import kimodo
    from kimodo.assets import skeleton_asset_path
    from kimodo.exports import MujocoQposConverter
    from kimodo.skeleton import G1Skeleton34
    loaded = Path(kimodo.__file__).resolve()
    integration_root = Path(__file__).resolve().parent
    require(integration_root in loaded.parents, f'Kimodo must load from this integration: {loaded}')
    body_order, sonic_repo = canonical_order(canonical_path)
    motion = load_motion(input_path)
    xml = Path(skeleton_asset_path('g1skel34', 'xml', 'g1.xml')).resolve(strict=True)
    skeleton = G1Skeleton34()
    converter = MujocoQposConverter(skeleton, str(xml))
    joints = ET.parse(xml).getroot().find('worldbody').findall('.//joint')
    source_names = [j.attrib['name'] for j in joints]
    require(len(source_names) == 29 and all(j.get('type', 'hinge') == 'hinge' for j in joints),
            'Converter XML must have exactly 29 scalar hinge joints')
    runtime_names = [name.replace('_skel', '_joint') for name in converter._mujoco_joint_including_root_list[1:]]
    require(runtime_names == source_names, 'Converter output order differs from inspected XML traversal')
    mapped_names = [skeleton.bone_order_names[int(i)].replace('_skel', '_joint')
                    for i in converter._mujoco_indices_to_kimodo_indices]
    require(mapped_names == source_names, 'Skeleton/converter name mapping disagrees with XML')
    permutation = joint_permutation(source_names, body_order)
    with torch.no_grad():
        qpos = converter.to_qpos(
            torch.as_tensor(motion['local_rot_mats'], dtype=torch.float32, device='cpu').unsqueeze(0),
            torch.as_tensor(motion['root_positions'], dtype=torch.float32, device='cpu').unsqueeze(0),
            root_quat_w_first=True, mujoco_rest_zero=False).detach().cpu().numpy()
    frames = len(motion['root_positions'])
    require(qpos.shape == (1, frames, 36) and np.isfinite(qpos).all(), 'Invalid converter qpos')
    qpos = qpos[0].astype(np.float64)
    checked_quaternions(qpos[:, 3:7])
    source_t = np.arange(frames, dtype=np.float64) / source_fps
    target_t = target_timestamps(source_t, target_fps)
    def linear(values):
        return np.column_stack([np.interp(target_t, source_t, values[:, i]) for i in range(values.shape[1])])
    body = linear(qpos[:, 7:][:, permutation])
    pos = linear(qpos[:, :3])
    quat = resample_quaternions(source_t, qpos[:, 3:7], target_t)
    arrays = {'timestamps': target_t, 'body_ref_q': body,
              'body_ref_dq': np.gradient(body, target_t, axis=0, edge_order=2),
              'root_ref_pos': pos, 'root_ref_quat': quat,
              'root_lin_vel': np.gradient(pos, target_t, axis=0, edge_order=2),
              'root_ang_vel': world_angular_velocity(quat, target_t)}
    warnings = ['Source FPS is an explicit assumption; NPZ contains no timestamps.',
                'Converter default raw DOFs retained (mujoco_rest_zero=False); no joint clamp or rest-offset adjustment.',
                'Phase 1 validates the intermediate numerically; canonical XML replay and physical validity remain later phases.']
    if np.any(np.abs(np.diff(qpos[:, 7:], axis=0)) > np.pi):
        warnings.append('Source joint DOFs contain a >pi step; linear interpolation retains it without guessing an unwrap.')
    metadata = {
        'phase': 1, 'reference_type': 'body_root_intermediate', 'complete_t7_reference': False,
        'source': 'Kimodo G1 smoke NPZ', 'source_path': str(input_path), 'source_sha256': file_hash(input_path),
        'source_fps': source_fps, 'source_frames': frames, 'source_start_time': 0.,
        'source_end_time': float(source_t[-1]), 'source_timestamps': 'arange(source_frames)/source_fps',
        'target_fps': target_fps, 'target_frames': len(target_t), 'quaternion_order': 'wxyz',
        'velocity_frame': 'world', 'body_joint_order': body_order, 'kimodo_joint_order': source_names,
        'kimodo_joint_name_to_index': {name: i for i, name in enumerate(source_names)},
        'canonical_body_joint_name_to_index': {name: i for i, name in enumerate(body_order)},
        'joint_permutation': permutation, 'permutation_definition': 'canonical body column i = converter joint column joint_permutation[i]',
        'velocity_derivation': 'derived finite difference, not measured MuJoCo velocity',
        'body_and_root_linear_difference': 'numpy.gradient at target timestamps; second-order central/endpoint differences',
        'root_angular_difference': 'world relative rotation q_next * inverse(q_current); rotvec/dt; adjacent interval average at interior timestamps; one-sided endpoint intervals',
        'position_interpolation': 'linear; no extrapolation', 'quaternion_interpolation': 'hemisphere-consistent SLERP',
        'hand_trajectory': 'absent / not included', 'hand_trajectory_fabricated': False,
        'root_position_source': 'root_positions; smooth_root_pos not substituted',
        'coordinate_conversion': 'MujocoQposConverter.to_qpos exactly once',
        'mujoco_rest_zero': False, 'joint_angle_convention': 'converter default raw joint_dofs',
        'kimodo_loaded_path': str(loaded), 'python_executable': sys.executable,
        'converter_source_path': str(Path(sys.modules[MujocoQposConverter.__module__].__file__).resolve()),
        'kimodo_xml_path': str(xml), 'kimodo_xml_sha256': file_hash(xml),
        'canonical_orders_source': str(Path(canonical_path).resolve()), 'canonical_orders_source_sha256': file_hash(canonical_path),
        'sonic_repo_for_orders': str(sonic_repo),
        'world_frame_evidence': 'canonical robot_state uses mj_jacBody rotational Jacobian jr @ qvel',
        'warnings': warnings,
        'limitations': 'This output is NOT a complete canonical T7 expert reference. Hand trajectory was NOT fabricated.'}
    metadata['validation'] = validate_arrays(arrays, body_order, metadata)
    write_output(output_path, arrays, metadata)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=BASE / 'outputs/g1_smoke_right_hand.npz')
    parser.add_argument('--output', type=Path, default=BASE / 'outputs/g1_smoke_t7_body_reference')
    parser.add_argument('--source-fps', type=float, default=30.)
    parser.add_argument('--target-fps', type=float, default=50.)
    parser.add_argument('--canonical-source', type=Path, default=CANONICAL)
    args = parser.parse_args()
    metadata = convert(args.input, args.output, args.source_fps, args.target_fps, args.canonical_source)
    print(json.dumps({'output': str(args.output), 'validation': metadata['validation'],
                      'joint_permutation': metadata['joint_permutation'], 'warnings': metadata['warnings']}, indent=2))


if __name__ == '__main__':
    main()
