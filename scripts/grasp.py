"""Supported physical grasp baseline; no object attachment or qpos teleporting."""
import numpy as np
import mujoco


class Grasp:
    def __init__(self, model, data):
        self.m, self.d = model, data
        self.plan = mujoco.MjData(model)
        self.plan.qpos[:] = data.qpos
        self.joints = model.actuator_trnid[:, 0]
        self.qa = model.jnt_qposadr[self.joints]
        self.va = model.jnt_dofadr[self.joints]
        self.home = data.qpos[self.qa].copy()
        self.arm = [model.joint('right_'+n+'_joint').id for n in
                    ['shoulder_pitch','shoulder_roll','shoulder_yaw','elbow','wrist_roll','wrist_pitch','wrist_yaw']]
        self.arm.insert(0,model.joint('waist_pitch_joint').id)
        self.aq = model.jnt_qposadr[self.arm]
        self.av = model.jnt_dofadr[self.arm]
        self.wrist = model.body('right_wrist_yaw_link').id
        self.cube = model.body('task_red_cube').id
        self.cube_geom = model.geom('task_cube_geom').id
        self.origin = data.xpos[self.cube].copy()
        self.hand = {n: model.joint('right_hand_'+n+'_joint').qposadr[0] for n in
                     ['thumb_0','thumb_1','thumb_2','middle_0','middle_1','index_0','index_1']}
        self.kp = np.array([12 if 'hand_' in model.joint(j).name else 180 for j in self.joints],float)
        self.kd = np.array([.3 if 'hand_' in model.joint(j).name else 5 for j in self.joints],float)
        self.start = data.xpos[self.wrist].copy()
        self.rotation = np.array([[1,0,0],[0,0,1],[0,-1,0]],float)
        self.target = self.origin - self.rotation @ np.array([.135,.065,0])
        self.thumb_pre=0.
        self.stage = ''

    def ik(self, target):
        m,d = self.m,self.plan
        jp,jr = np.zeros((3,m.nv)),np.zeros((3,m.nv))
        for _ in range(60):
            mujoco.mj_forward(m,d)
            r = d.xmat[self.wrist].reshape(3,3)
            er = sum(np.cross(r[:,i],self.rotation[:,i]) for i in range(3))*.5
            error = np.r_[target-d.xpos[self.wrist], .3*er]
            if np.linalg.norm(error)<1e-5: break
            mujoco.mj_jacBody(m,d,jp,jr,self.wrist)
            jac = np.vstack([jp[:,self.av],.3*jr[:,self.av]])
            dq = jac.T@np.linalg.solve(jac@jac.T+np.eye(6)*1e-3,error)
            old=d.qpos[self.aq].copy()
            free=np.ones(len(self.arm),dtype=bool)
            for _ in range(len(self.arm)):
                blocked=((old<=m.jnt_range[self.arm,0]+1e-5)&(dq<0))|((old>=m.jnt_range[self.arm,1]-1e-5)&(dq>0))
                if not np.any(blocked & free):break
                free &= ~blocked
                jf=jac[:,free]
                dq[:]=0
                dq[free]=jf.T@np.linalg.solve(jf@jf.T+np.eye(6)*1e-3,error)
            old_cost=np.linalg.norm(target-d.xpos[self.wrist])**2+.045*np.linalg.norm(r-self.rotation)**2
            dq *= min(1., .1 / max(np.max(np.abs(dq)), 1e-12))
            for step in [1,.5,.25,.1]:
                d.qpos[self.aq] = np.clip(old+step*dq,m.jnt_range[self.arm,0],m.jnt_range[self.arm,1])
                mujoco.mj_forward(m,d)
                cost=np.linalg.norm(target-d.xpos[self.wrist])**2+.045*np.linalg.norm(d.xmat[self.wrist].reshape(3,3)-self.rotation)**2
                if cost<old_cost:break
            else:
                d.qpos[self.aq]=old
                break

    def control(self,t):
        def smooth(a,b,u):
            u=np.clip(u,0,1);return a+(b-a)*(u*u*(3-2*u))
        above = self.target + [0,0,.13]
        if t<2:
            stage='reach'; target=smooth(self.start,above,t/2); close=0
        elif t<4:
            stage='lower'; target=smooth(above,self.target,(t-2)/2); close=0
        elif t<6:
            stage='close'; target=self.target; close=smooth(0,1,(t-4)/2)
        elif t<8:
            stage='lift'; target=smooth(self.target,self.target+[0,0,.16],(t-6)/2); close=1
        else:
            stage='hold'; target=self.target+[0,0,.16]; close=1
        angle=smooth(0,-np.pi/2,t/2)
        c,s=np.cos(angle),np.sin(angle)
        self.rotation=np.array([[1,0,0],[0,c,-s],[0,s,c]])
        self.ik(target)
        for name, val in zip(self.hand,[0,-1,-1.25,1.2,1.2,1.2,1.2]):
            closure=self.thumb_pre+(1-self.thumb_pre)*close if name.startswith('thumb') else close
            self.plan.qpos[self.hand[name]]=closure*val
        self.stage=stage

    def apply(self):
        ref=self.plan.qpos[self.qa]
        torque=self.kp*(ref-self.d.qpos[self.qa])-self.kd*self.d.qvel[self.va]+self.d.qfrc_bias[self.va]
        limits=self.m.jnt_actfrcrange[self.joints]
        self.d.ctrl[:]=np.clip(torque,limits[:,0],limits[:,1])

    def contacts(self):
        names=[]
        for c in self.d.contact:
            other=c.geom2 if c.geom1==self.cube_geom else c.geom1 if c.geom2==self.cube_geom else -1
            if other>=0: names.append(self.m.body(self.m.geom_bodyid[other]).name)
        return names
