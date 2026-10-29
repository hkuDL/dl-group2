# SONIC 源码差异

仅保存文本补丁，不含 native binary、模型 encoder/decoder 或 SDK binary。上游代码许可见 SONIC_LICENSE、ARDY_LICENSE。模型权重另有其适用许可，未包含在此恢复包中。

| 补丁 | 基线与用途 |
|---|---|
| `sonic-project.patch` | 官方 `NVlabs/GR00T-WholeBodyControl` 基线 `b042411fae38ee4d1af9aac82a37a1f8d14d6dd0` → 服务器提交 `39ea4bc6feffc72a752dff3766e38edd910524f1`；7 个源码文件，MUSA 构建与推理适配 |
| `sonic-hot-reload.patch` | 相对于服务器上述提交的在线 VLM 分支变化；3 个源码文件；分段 reference hot continuation，与离线主比较分开 |
| `sonic-instrumentation.patch` | 服务器保存的 native trace 差异，用于来源审查；实际构建应由 `canonical_va.native_build` 在独立目录生成，并验证 anchors，不手工叠加到共享控制器 |

在独立的官方源码 checkout 中，先检出上述基线，再检查并应用项目补丁。以下命令从 `simulation/` 执行，要求独立的外部 checkout 已放在 `GR00T-WholeBodyControl/`；不要对服务器正在使用的控制器目录操作。

```bash
git -C GR00T-WholeBodyControl rev-parse HEAD
git -C GR00T-WholeBodyControl apply --check ../patches/sonic-project.patch
git -C GR00T-WholeBodyControl apply ../patches/sonic-project.patch
```

应用源码差异并不等于完成编译、模型转换、SDK 配置或机器人批准。hot-reload 只在独立的 VLM 研究 checkout 使用；不得事后替换 Oct.8 固定比较的控制器。原 `native_build/` 的生成源码副本和编译产物均未提交。
