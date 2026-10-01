"""Compose upstream G1 and our environment without editing third_party."""
from pathlib import Path
import xml.etree.ElementTree as ET
import mujoco

ROOT = Path(__file__).resolve().parents[1]
ROBOT = ROOT / 'third_party/GR00T-WholeBodyControl/decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml'
SCENE = ROOT / 'scenes/tabletop.xml'


def load_scene(supported=False):
    robot = ET.parse(ROBOT).getroot()
    # Resolve assets against their original XML, not the caller's working directory.
    # This pinned upstream robot is self-contained; fail clearly if that changes.
    if robot.find('.//include') is not None:
        raise RuntimeError('Upstream robot now contains includes; update asset resolution.')
    compiler = robot.find('compiler')
    for kind, directory in [('mesh', 'meshdir'), ('texture', 'texturedir')]:
        base = ROBOT.parent / compiler.get(directory, '')
        for asset in robot.findall(f'asset/{kind}'):
            if asset.get('file'):
                asset.set('file', str((base / asset.get('file')).resolve()))
        compiler.attrib.pop(directory, None)
    environment = ET.parse(SCENE).getroot()
    # Separate project visuals from upstream collision geoms (group 0).
    for geom in environment.findall('.//geom'):
        geom.set('group','2')
    robot.set('model', environment.get('model'))
    robot.extend(list(environment))
    # Sensor cameras are project-owned attachments; upstream XML is never written.
    torso=robot.find(".//body[@name='torso_link']")
    wrist=robot.find(".//body[@name='right_wrist_yaw_link']")
    ET.SubElement(torso,'camera',name='head_rgb',pos='0.06 0 0.44',
                  xyaxes='0 -1 0 0.707107 0 0.707107',fovy='75')
    ET.SubElement(wrist,'camera',name='wrist_rgb',pos='0.06 -0.09 0.13',
                  xyaxes='-0.866186 0 -0.499722 0.359 -0.696 -0.623',fovy='90')
    if supported:
        equality = ET.SubElement(robot, 'equality')
        ET.SubElement(equality, 'weld', name='debug_pelvis_support', body1='pelvis', solref='0.005 1')
    model = mujoco.MjModel.from_xml_string(ET.tostring(robot, encoding='unicode'))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data
