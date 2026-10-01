"""Check nominal supported grasp and an open-hand negative control."""
import contextlib
import io
import json
import mujoco
from scene import load_scene
from pick_red_cube import Episode


def run(close_hand):
    model,data=load_scene(supported=True)
    episode=Episode(model,data)
    if not close_hand:
        original=episode.controller.control
        def open_hand(t):
            original(t)
            for address in episode.controller.hand.values():
                episode.controller.plan.qpos[address]=0.
        episode.controller.control=open_hand
    with contextlib.redirect_stdout(io.StringIO()):
        while data.time<11:episode.step()
    result=episode.report()
    print(json.dumps({'close_hand':close_hand,**result},indent=2))
    return result


if __name__=='__main__':
    positive=run(True)
    negative=run(False)
    assert positive['success'], 'Nominal physical grasp failed'
    assert not negative['success'], 'Open hand unexpectedly passed grasp criterion'
    print('PASS: nominal physical grasp and open-hand negative control')
