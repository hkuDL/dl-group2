# DASC7606C Track 4：Archon 监督参观记录与检查表

> 建议参观日期：2026-09-29  
> 课程文件：`DASC7606C Group Project Modified.pdf`  
> 小组方向：Track 4 - Humanoid-Robot Motion Generation Deployment

## 1. 参观目标

本次参观不是普通实验室参观，也不要求现场训练新 policy 或把本组的 Kimodo、ARDY、SONIC 系统部署到真机。小组需要在工作人员监督下，使用或观察 Archon 提供的系统，理解以下两个真实机器人工作流程：

1. **Demonstration recording：**操作者如何控制机器人完成示范，以及系统记录什么数据。
2. **Policy inference：**训练好的 policy 如何读取输入、输出动作并通过控制系统驱动机器人。

最终报告需要准确解释：

- 系统输入；
- demonstration 中记录的数据；
- policy/model 的输出；
- 模型输出到机器人动作的完整控制流程。

## 2. 需要观察的整体流程

### 2.1 Demonstration-recording workflow

```text
操作者
  -> 遥操作设备或用户接口
  -> 机器人执行动作
  -> 相机与机器人传感器采集数据
  -> 保存为一个 demonstration episode
  -> 质量检查、成功/失败标记和重录
```

### 2.2 Policy-inference workflow

```text
任务信息 + 相机观测 + 机器人状态
  -> 数据预处理
  -> 已训练 policy
  -> model output / action
  -> action adapter 或安全过滤
  -> low-level controller
  -> 机器人关节与 hand/gripper
  -> 新观测与下一次预测
```

## 3. 基本信息

| 项目 | 现场记录 |
|---|---|
| 参观日期与时间 | |
| 参观地点 | |
| 现场指导人员 | |
| 本组出席成员 | |
| 机器人型号 | |
| Hand/gripper 类型 | |
| 操作者接口或遥操作设备 | |
| 相机及其他传感器 | |
| 现场演示任务 | |
| 是否允许拍照 | 是 / 否 / 部分允许 |
| 是否允许录像 | 是 / 否 / 部分允许 |
| 是否允许在报告或公开仓库使用材料 | 是 / 否 / 需再次确认 |

## 4. Demonstration Recording 记录表

### 4.1 操作者输入与启动流程

- [ ] 使用了什么设备：手柄 / VR / 键盘 / 动作捕捉 / 其他：__________
- [ ] 操作者控制的是关节、末端位姿、速度，还是更高层任务？
- [ ] 开始前是否需要机器人 calibration 或 homing？
- [ ] 如何 reset 机器人和场景？
- [ ] 如何开始、暂停、停止一次 recording？
- [ ] 如何定义一个 episode 的开始和结束？
- [ ] 操作者如何控制 hand/gripper？是否与手臂分开？
- [ ] demonstration 过程中是否提供相机或状态反馈？

现场记录：

```text

```

### 4.2 Demonstration 数据字段

这里的目标是记录“保存了哪些字段及其含义”，不要求复制或下载原始机器人数据。

| 数据类别 | 是否记录 | 表示形式、shape、单位或备注 |
|---|---|---|
| RGB image | 是 / 否 / 未确认 | |
| Depth image | 是 / 否 / 未确认 | |
| Camera ID、视角和内外参 | 是 / 否 / 未确认 | |
| Joint position | 是 / 否 / 未确认 | |
| Joint velocity | 是 / 否 / 未确认 | |
| Joint torque/effort | 是 / 否 / 未确认 | |
| Base/root pose | 是 / 否 / 未确认 | |
| End-effector pose | 是 / 否 / 未确认 | |
| Operator command | 是 / 否 / 未确认 | |
| Robot executed action | 是 / 否 / 未确认 | |
| Hand/gripper state | 是 / 否 / 未确认 | |
| Contact/force information | 是 / 否 / 未确认 | |
| Timestamp | 是 / 否 / 未确认 | |
| Episode boundary | 是 / 否 / 未确认 | |
| Task ID 或自然语言指令 | 是 / 否 / 未确认 | |
| Success/failure label | 是 / 否 / 未确认 | |
| Failure reason | 是 / 否 / 未确认 | |

### 4.3 数据同步、保存与质量控制

| 问题 | 现场记录 |
|---|---|
| 图像、状态和动作如何通过 timestamp 对齐？ | |
| Recording/control frequency 是多少？ | |
| Action 代表操作者命令还是机器人实际执行结果？ | |
| 数据以什么文件或数据集格式保存？ | |
| 一个 episode 的目录或字段结构是什么？ | |
| 如何判断 demonstration 是否合格？ | |
| 失败 episode 会删除、保留还是打标签？ | |
| 是否有人工 review 或自动质量检查？ | |
| 是否会因为遮挡、延迟或传感器问题重新录制？ | |

如果某项信息未提供或不允许记录，请写“未提供”或“受限”，不要自行猜测。

## 5. Policy Inference 记录表

### 5.1 Policy 输入

| 输入项目 | 是否使用 | 预处理或备注 |
|---|---|---|
| RGB image | 是 / 否 / 未确认 | |
| Depth image | 是 / 否 / 未确认 | |
| 多相机图像 | 是 / 否 / 未确认 | |
| Joint position/velocity | 是 / 否 / 未确认 | |
| Base/root state | 是 / 否 / 未确认 | |
| Hand/gripper state | 是 / 否 / 未确认 | |
| Task ID | 是 / 否 / 未确认 | |
| 自然语言指令 | 是 / 否 / 未确认 | |
| 历史 observation/action | 是 / 否 / 未确认 | |

需要询问的预处理：

- [ ] 图像是否 resize、crop、normalize？
- [ ] 是否使用连续多帧或 frame stacking？
- [ ] Robot state 是否 normalize？
- [ ] 文本或 task ID 如何编码？
- [ ] 输入数据是否与 demonstration recording 保持相同格式？

### 5.2 Model 输出

确认模型实际输出哪一种或哪几种表示：

- [ ] Joint position target
- [ ] Joint velocity
- [ ] Torque
- [ ] End-effector position/orientation
- [ ] Action chunk
- [ ] Trajectory
- [ ] Latent motion token
- [ ] Hand/gripper command
- [ ] Whole-body motion
- [ ] 其他：__________

| 问题 | 现场记录 |
|---|---|
| 一次 inference 输出一个动作还是一段 action chunk？ | |
| 输出包含多少时间步？ | |
| Policy inference frequency 是多少？ | |
| Robot control frequency 是多少？ | |
| 是否不断读取新观测并重新预测？ | |
| 模型输出是否需要 IK、retargeting 或其他 adapter？ | |
| 是否对输出进行 smoothing、clipping 或 safety filtering？ | |
| Hand/gripper 是否由独立输出或独立控制分支负责？ | |

## 6. Robot Control Flow

参观结束前，应当能够补全下面的控制链路：

```text
[任务输入：________________]
  -> [传感器观测：________________]
  -> [预处理：________________]
  -> [Policy/model：________________]
  -> [模型输出：________________]
  -> [Adapter/planner：________________]
  -> [Low-level controller：________________]
  -> [Robot joints：________________]
  -> [Hand/gripper branch：________________]
```

### 6.1 上下半身与手部控制

| 问题 | 现场记录 |
|---|---|
| Policy 控制全身还是只控制上半身？ | |
| 下半身是 joint lock、standing reference 还是动态平衡？ | |
| 上下半身是否由同一个 low-level controller 控制？ | |
| Hand/gripper 是否使用单独 controller？ | |
| 手部命令如何与手臂动作同步？ | |
| 现场系统是否使用 SONIC？如果不是，使用什么？ | |

注意：不要预设 Archon 现场一定使用 SONIC。应记录现场真实控制链路，再与本组的 SONIC 仿真方案比较。

## 7. 安全、停止与恢复

- [ ] Emergency stop 在哪里，由谁操作？
- [ ] 是否设置 joint limits、velocity limits 或 workspace limits？
- [ ] 是否有 collision detection 或 safety filtering？
- [ ] 机器人失衡或动作异常时如何停止？
- [ ] 停止后如何 reset 或 recovery？
- [ ] 推理前是否有人工确认步骤？
- [ ] 工作人员与机器人之间的安全距离如何规定？

现场记录：

```text

```

## 8. 成功与失败案例

### 8.1 成功案例

| 项目 | 记录 |
|---|---|
| 任务 | |
| 输入 | |
| 模型输出 | |
| 控制流程 | |
| 是否一次成功 | |
| 是否需要人工纠正 | |
| 大致响应时间 | |
| 成功证据或允许使用的材料 | |

### 8.2 失败或恢复案例

可以记录实际观察到的失败，也可以记录工作人员说明的典型失败。

| 项目 | 记录 |
|---|---|
| 失败发生在哪个阶段 | |
| 失败现象 | |
| 可能原因 | |
| 是否触发安全机制 | |
| 如何停止和恢复 | |
| 是否需要重新 recording/inference | |
| 对本组仿真项目的启示 | |

可关注的失败类型：视觉遮挡、目标识别错误、手部未对准、夹爪时序错误、动作不平滑、控制延迟、关节越界、碰撞、失衡、数据不同步和人工停止。

## 9. 与本组 Track 4 项目的比较

本组计划的核心流程为：

```text
Typed text
  -> Kimodo 或 ARDY
  -> Canonical motion adapter
  -> SONIC
  -> Unitree G1 simulation
  -> Separate hand/gripper control
```

| 比较项 | Archon 现场系统 | 本组方案 | 相同点或差异 |
|---|---|---|---|
| Task input | | Typed text | |
| Visual observation | | Core 可使用仿真 ground-truth；视觉扩展属于 Bonus | |
| Robot state | | Simulation state | |
| Motion/policy model | | Kimodo / ARDY | |
| Model output | | Canonical G1 reference motion | |
| Motion adapter | | Canonical motion adapter | |
| Low-level controller | | SONIC | |
| Lower-body stabilization | | SONIC standing/whole-body stabilization strategy | |
| Hand/gripper control | | Separate synchronized branch | |
| Safety and limits | | Simulation joint/workspace limits | |
| Failure recovery | | Reset/replan/retry | |

## 10. 建议现场提问

如果时间有限，优先询问以下问题：

1. Demonstration recording 时，操作者通过什么设备输入什么命令？
2. 每个 episode 记录哪些 observation、robot state 和 action？
3. Action 是操作者命令、控制器目标，还是机器人实际执行结果？
4. 图像、状态和动作如何同步？
5. Policy inference 时，模型的实际输入是什么？
6. 模型输出是 joint target、end-effector pose、action chunk 还是其他表示？
7. 模型输出如何转换为机器人控制命令？
8. Hand/gripper 是否走独立控制分支？
9. 只控制上半身时，下半身如何保持稳定？
10. Inference 是闭环控制还是预先生成完整轨迹？
11. 失败 episode 如何处理，policy 失败后如何恢复？
12. 哪些笔记、照片、截图或非敏感 metadata 可以用于课程报告？

## 11. 现场分工建议

| 小组 | 现场重点 |
|---|---|
| Team 1：Meng Guanlin、Fu Yuhan、Luo Mingdi | 机器人硬件、传感器、控制链路、上下半身稳定和 hand/gripper control |
| Team 2：Hao Hao、Tang Zichun、Zhang Kunqi | Demonstration recording、数据字段、episode 结构和数据质量控制 |
| Team 3：Li Jingyao、Huang Xinxuan、Zhang Yuanzhuo | Policy inference、模型输入输出、预处理、动作适配和闭环方式 |
| Team 4：Zhang Yixin、Mi Siyuan、Tu Chengyuan | 统一笔记、成功/失败案例、安全流程、权限确认和报告证据 |

## 12. 权限与数据管理

- [ ] 拍照前已获得明确许可。
- [ ] 录像前已获得明确许可。
- [ ] 已确认哪些材料只能用于课程报告，哪些可以进入公开 GitHub。
- [ ] 未记录或公开账号、密码、API key 或其他 credentials。
- [ ] 未复制受限机器人数据、内部代码或未经授权的模型文件。
- [ ] 未记录未经同意的工作人员个人信息或声音。
- [ ] 对不能公开的内容已标注“受限”或“仅供课程报告使用”。

## 13. 参观结束前的完成检查

- [ ] 一张完整的 demonstration-recording 流程图；
- [ ] 一张完整的 policy-inference 流程图；
- [ ] 一张 demonstration 数据字段表；
- [ ] 一张 policy 输入和 model 输出表；
- [ ] Low-level controller、hand/gripper 和 lower-body stabilization 说明；
- [ ] Emergency stop、安全过滤和 recovery 说明；
- [ ] 至少一个成功案例；
- [ ] 至少一个失败或工作人员说明的典型失败案例；
- [ ] Archon 与本组 Kimodo/ARDY -> SONIC 流程的比较；
- [ ] 所有照片、视频、截图和数据样例均有明确使用权限；
- [ ] 所有无法确认的字段均标记为“未提供”，没有自行推测。

## 14. 参观后的一段式总结模板

```text
本组于____________在监督下参观 Archon，并体验/观察了____________机器人系统的
demonstration-recording 与 policy-inference 工作流程。Demonstration 由____________作为
操作者输入，系统同步记录____________，并以____________组织为 episode。Policy inference
以____________作为输入，输出____________，随后经过____________转换并由____________
low-level controller 执行。Hand/gripper 由____________控制，下半身通过____________保持稳定。
现场观察到的成功案例是____________；失败或恢复案例是____________，其主要原因及处理方式为
____________。与本组 Kimodo/ARDY -> canonical adapter -> SONIC 仿真流程相比，主要相同点为
____________，主要差异为____________。
```
