# Task 9 Profiling 记录规范

版本：`v0.3-ready-for-offline-tests`。这是性能测量规范，不是抓取成功率评估器，也不代表已经完成服务器 smoke。正式比较仍需冻结两种方法的入口、场景、初始状态、指令、候选预算、时长、试验次数和重试规则。

## 1. 文件与使用

将本文件、`profiling_schema.json`、`summarize_profile.py` 放在同一目录。需要 Python 3.10+，只使用标准库，无需安装 jsonschema。脚本从相邻 schema 读取结构约束，并校验时间、DDS 状态及 run 一致性。

内置 schema 解释器只实现本 schema 使用的关键字，不是通用 JSON Schema 引擎；不支持的校验关键字会报错。schema 本身采用 Draft 2020-12 格式，也可以交给标准 validator。跨字段检查仍需运行本脚本。

Linux 示例（Windows 也可运行同一行命令）：

```bash
python summarize_profile.py profile_events.jsonl --run-type not_final_smoke --json-out smoke_summary.json --csv-out smoke_summary.csv
python summarize_profile.py ardy_events.jsonl kimodo_events.jsonl --manifest profile_manifest.json --run-type formal --experiment-id exp001 --json-out formal_summary.json --csv-out formal_summary.csv
```

输出路径必须尚不存在，且不能覆盖任何输入。退出码：0=校验及指定覆盖检查通过（无 manifest 时完整性仍未验证）；1=格式、身份、重复记录或参数错误；2=已生成报告，但 manifest 覆盖检查失败。退出码不是抓取成功判定。

v0.1/v0.2 日志不再直接接受。不可只改版本号：需要根据真实记录补全实验身份和计时元数据，无法恢复的信息保持未知；无法确定身份的旧数据仅作开发档案，不进入正式比较。

## 2. 观察边界与当前代码事实

性能测量不能改变候选选择、控制命令、物理、评估规则。当前已读取的回放链路是：

```text
ARDY / Kimodo 离线生成 → adapter / reference 导出
→ SONIC DDS 身体控制 + 独立 HandTrajectoryController
→ MuJoCo → PhysicalGraspEvaluator → report / metadata
```

SONIC reference 名义 50 Hz，物理与手部控制名义 200 Hz，具体运行值必须保存。`GraspEvidence` 尚未在已检查入口中发现；该 stage 只在实际调用该组件时启用，不得虚构事件。

`expert_valid` 包含源数据认证条件，不能代替 T9 模型成功率。独立 TrialLog 应保留每次尝试、运行状态、协议符合情况、物理结果、错误和证据路径；通过 `run_id` 关联本日志。profiling 工具不计算成功率。

## 3. 身份与可比条件

每个事件一行 JSONL，必须遵守 schema。新增字段：

| 字段 | 定义 |
|---|---|
| `event_id` | 全输入唯一，建议 `run_id:process:stage:clock:counter` |
| `experiment_id` | 同一冻结实验批次 |
| `config_id` | 公共协议/比较条件标识，建议冻结配置哈希；不能是随意相同的标签 |
| `run_id` | 一次实际尝试的唯一 ID，与 TrialLog 一致 |
| `trial_index` | 同一方法/实验/条件/case 下的非负整数，重试也需新的编号 |
| `run_type` | `not_final_smoke`、`pilot`、`formal` |

方法 checkpoint、adapter、精度、候选数量、生成帧数、去噪步数、warm/cold、GPU 卡数/共享状态、渲染开关、CPU 线程、SONIC/场景哈希、同步及采样策略，应记录在 TrialLog/provenance；可影响公平比较的公共设置纳入 config_id。两个方法可使用不同 checkpoint，但需固定并披露。不得把不同预算隐藏在同一 config_id 下。

`hardware_id` 表示稳定主机/资源身份；实际物理 device ID 另存 accelerator。主机不同、CPU wall 与 GPU event 不同、是否含 profiling 开销不同的记录不合并。GPU 逻辑编号 `musa:0` 不等于物理卡号。

最小 CPU 事件示例（仅为格式示例，不是测量结果）：

```json
{"schema_version":"t9_profile_event_v0.3","event_id":"r1:gen:0","experiment_id":"exp001","config_id":"protocol_hash","run_id":"r1","method":"ardy","run_type":"not_final_smoke","case_id":"center","trial_index":0,"scope":"generation","stage":"generation_total","clock":"perf_counter_ns","start_ns":1000000,"end_ns":2000000,"duration_ms":1.0,"deadline_ms":null,"frame_index":null,"process_id":123,"thread_id":1,"device":"cpu","hardware_id":"worker00038","synchronized":false,"profile_overhead_included":false,"accelerator":null,"transport":null,"tags":{}}
```

`accelerator`、`transport` 顶层字段必须出现，不适用时为 null；为对象时所有定义字段均需出现，允许的未知值用 null。不得用 0、false 或空字符串伪造已知事实。GPU event 的 accelerator 必須为非空有效对象，device_count 至少为 1。CPU wall 计时覆盖 GPU 子进程时，也应填写已知 accelerator 信息；它仍是 wall time，不是 GPU kernel 时间。

## 4. 计时与阶段

CPU 使用 `time.perf_counter_ns()` 或 C++ `steady_clock`，start/end 必须来自同一进程、同一时钟域；duration 与其一致。GPU 使用 MUSA/CUDA event，elapsed time 必须在 event 完成同步后读取；GPU start_ns/end_ns 为 null，不将 GPU event 数值伪装成 CPU 时间戳。UTC 时间只用于 provenance。

整个生成子进程的 wall time 包含等待、加载等的范围必须说明；模型内部 GPU event 另记，二者不能混算。不要为了计时在每个在线控制步加入同步屏障。SONIC 内部无可靠埋点时不记录 encoder/policy event，TrialLog/manifest 说明未测，不填 0。

建议阶段：

| scope | stage 示例 |
|---|---|
| generation | prompt_parse、model_generate、candidate_select、generation_total |
| candidate_preparation | adapter、reference_export、candidate_preparation_total |
| initialization | model_load、scene_load、controller_startup、warmup、reset |
| control_step | dds_state_publish_bundle、dds_command_read、body_pd、hand_control、mujoco_step、mujoco_forward、physical_evaluator、loop_compute_total、pacing_sleep |
| episode | execution、episode_total |
| postprocess | video_render、artifact_write、postprocess_total |

完整允许值见 schema。阶段必须属于对应 scope。嵌套 total 与子阶段存在重叠，不能相加求总时间。frame_index 是 run 内从零递增的物理步编号，control_step 必填，其他 scope 为 null；跨初始化与播放保持唯一，不能在播放时重置后复用同一编号。

loop_compute_total 应覆盖整个循环的计算与同步 I/O，但排除 pacing_sleep；若另外测物理子调用，避免误将其当作完整循环预算。现有回放默认在循环中读 CSV、打印、渲染并编码视频，这些开销不能遗漏。首轮可统一关闭图像并事后渲染，正式协议应固定设置。

200 Hz 的 5 ms 是循环计算预算，不自动等于每个子阶段的 deadline；SONIC 50 Hz 的 20 ms 属于另一层。deadline_ms 必须明确其作用范围，子阶段没有指定预算时为 null。miss 定义为 duration > deadline；不据此宣称已测得完整实时调度性能。

## 5. DDS 与资源测量

当前 bridge 没有接收时间戳/递增计数，不能仅凭 low_cmd_received 或 new_low_cmd 推导每步新消息。后续实现应在接收回调、同一把锁下记录本机 monotonic 接收时间和 rx_counter；控制循环读取 command 与这些字段的一致快照。埋点不改变 command 或控制分支。

transport 的语义：

- new_command：接收计数相对上次读取有增长。
- reused_previous_command：没有新到达，继续使用已收到的命令。
- missing_command：尚无可用命令；age 为 null。
- command_age_ms：读取时刻减本机最后接收时刻。
- command_interval_ms：最后两次接收回调时间之差，不是两次 read 之差。
- stale_command：已知 age > 正的 stale_threshold_ms；任何一项不可用时保持 null。
- 所有指标都是接收侧观察；计数跳跃不等于网络丢包，也不能测得 state-to-command 因果延迟。

间隔汇总仅取 new_command=true 的读取样本；若两次读取间收到多条，只能看到最后一次间隔，不能声称覆盖全部到达。需要全部到达分布时另存接收日志。新/复用/缺失在已知状态下互斥，stale 可与复用重叠；未知也不能当成 false。

`PublishLowState()` 发布多个 topic。整函数使用 `dds_state_publish_bundle`，transport.topic 可为 null；只计 rt/lowstate 内部 Write 才使用单 topic 的 `dds_state_publish`。

S4000 资源可由 mthreads-gmi 独立低频采样。记录工具、频率、窗口、device、卡数、后端/实际 execution provider、dtype、warmup_runs、共享状态、显存测量范围。不能根据 ONNX 文件名推断 GPU provider。缺资源值保留 null。汇总的资源统计是已记录值的描述，不是时间加权利用率；重复记录相同峰值不会增加独立证据。

## 6. 完整性清单

无 manifest 的 smoke 允许汇总，但标为 coverage_status=unverified。formal 必须提供 manifest。manifest 应来自调度器的计划清单及真实终态，不能从成功日志反推，否则会漏掉完全没有事件的失败。

每个计划 run 包含身份、status（completed/failed/timeout/not_started）、failure_reason 和明确覆盖要求。completed 指运行完成，不表示抓取成功，此时 `failure_reason` 必须为 null；失败、超时和未启动需要非空原因，可没有测量事件且不得补零。中途失败仅检查当时按设计应有的阶段；失败之前的观测可用于诊断，但不能与完整运行直接作性能排名。同一 run 不得重复声明相同 scope/stage/clock 的覆盖要求。

```json
{
  "schema_version": "t9_profile_manifest_v0.3",
  "runs": [{
    "run_id": "r1", "experiment_id": "exp001", "config_id": "protocol_hash",
    "method": "ardy", "run_type": "not_final_smoke", "case_id": "center", "trial_index": 0,
    "status": "completed", "failure_reason": null,
    "requirements": [
      {"scope": "generation", "stage": "generation_total", "clock": "perf_counter_ns", "expected_count": 1},
      {"scope": "control_step", "stage": "loop_compute_total", "clock": "perf_counter_ns", "expected_count": 3200, "frame_start": 0, "frame_stride": 1}
    ]
  }]
}
```

上例 3200 仅说明格式，不是当前项目既定帧数。实际计数应按阶段、起止边界及采样计划填写；不能把 50 Hz reference 帧数当成 200 Hz physics 步数。frame_start/stride 提供时检查完整序列，重复 control-step 样本也拒绝。GPU 异步 stage 如不按每步记录，应另定义明确 expected_count。

覆盖通过仅表示满足清单中列出的要求，不能证明清单设计合理或物理任务成功。全部 planned run 都失败且事件文件为空时，仍可提供非空 manifest 来保留这些 run。

## 7. 输出和统计解释

- groups：逐 run、case、阶段、时钟、硬件、accelerator 设置、deadline、开销口径和 DDS 设置的统计。包含 event_count、mean/P50/P95/P99/min/max、deadline miss、DDS 已知样本分母和 true 次数、age/interval、资源记录描述。run_status 与 coverage_ok 也参与分组，失败、完成和覆盖不完整的运行不会混合汇总；无 manifest 时状态为 unknown。
- condition_groups：相同条件下，每个 run 的平均耗时再统计，每个 run 权重相同。它不是池化事件的 P95，也不是每个 trial 的端到端延迟，除非该 stage 恰好每 run 一个事件。
- runs：manifest 中的全部所选 run，包括无日志的失败/未启动，及覆盖问题。
- CSV 导出逐 run groups；无事件 run 只保存在 JSON 的 runs 中。因此正式分析必须保留 JSON。

脚本不把多个 case 汇总成排名，也不计算成功率。控制步数量不是独立试验次数。缺失值、未达到阶段、被过滤事件必须披露。所有输入先校验，再过滤；过滤不会让损坏或重复输入悄悄通过。正式输出包含未完成运行时，仅作检查报告，正式性能对比必须按预先协议处理并披露。

## 8. Profiling 自身验收与上线顺序

1. 离线人工事件验证：schema、条件分离、重复、覆盖、未知值、失败 run 和导出。人工数据必须标为 synthetic，不进入实验结果。
2. 核实服务器实际 scene/model/SONIC 路径和可用固定 reference，解决路径差异后再运行。
3. 同一输入/配置先关闭再开启 profiling 做 smoke。输入/reference/hash 严格一致；比较完成帧、物理结果、轨迹偏差、DDS 状态与墙钟开销。
4. 异步控制输出未证明位级确定时，state/action 哈希不同只触发分析，不自动判失败；先测无埋点重复运行的波动，预先确定允许误差。
5. 控制循环内仅做轻量内存记录，运行后落盘；测量记录开销、缓冲上限和丢弃数。降低采样频率时同时更新 manifest。
6. 通过固定 reference 验证后，再接入 ARDY/Kimodo，冻结正式协议。T7 未完成不阻塞前两步。

本版尚未向服务器插入埋点，没有生成任何真实耗时或抓取结果。
