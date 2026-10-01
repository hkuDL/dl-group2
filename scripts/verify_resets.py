"""Verify full reset isolation and case-dependent targets without rendering."""
import numpy as np
from cases import read_cases,reset_case
from scene import load_scene
from pick_red_cube import Episode


def main():
    config=read_cases();m,d=load_scene(supported=True)
    for case in config['cases']:
        reset_case(m,d,case)
        expected=d.qpos.copy()
        first=Episode(m,d);first.controller.control(0)
        ref=first.controller.plan.qpos.copy()
        for _ in range(20):first.step()
        d.qfrc_applied[:]=2;d.xfrc_applied[:]=3;d.ctrl[:]=1
        reset_case(m,d,case)
        fresh=Episode(m,d);fresh.controller.control(0)
        assert np.array_equal(d.qpos,expected)
        assert d.time==0 and np.count_nonzero(d.qvel)==0 and np.count_nonzero(d.ctrl)==0
        assert np.count_nonzero(d.qfrc_applied)==0 and np.count_nonzero(d.xfrc_applied)==0
        assert fresh.steps==0 and fresh.hold==0
        assert np.array_equal(fresh.controller.plan.qpos,ref)
        assert np.allclose(d.xpos[m.body('task_red_cube').id,:2],case['block_xy'])
        assert np.allclose(fresh.controller.origin[:2],case['block_xy'])
        print('PASS full reset:',case['id'])
    invalid={'id':'outside','block_xy':[10,0],'block_yaw_deg':0}
    try:reset_case(m,d,invalid)
    except ValueError:print('PASS rejects off-table case')
    else:raise AssertionError('Off-table placement accepted')


if __name__=='__main__':main()
