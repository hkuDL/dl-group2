## ardy2sonic
su - mccxadmin
<ADMIN_PASSWORD>
sudo docker ps
sudo docker exec -it 8a /bin/bash


cd group2/workspace/fuyuhan/ardy
copy run_generate.txt -> terminal, 修改prompt和输出路径
此时会在 ardy/outputs 文件夹下生成 .npz 和 .csv 文件
copy run_ardy_2_sonic.txt-> terminal 修改输入/输出路径 文件名

检查GR00T-WholeBodyControl/gear_sonic_deploy/reference/ardy路径下是否有对应的文件夹

跑 VNC
/usr/bin/websockify   --web=/usr/share/novnc   0.0.0.0:6080   127.0.0.1:5901

打开 6080->vnc.html, 连线密码 <VNC_PASSWORD>
terminal 运行
DISPLAY=:1 python gear_sonic/scripts/run_sim_loop.py --scene-path gear_sonic/data/robot_model/model_data/g1/scene_43dof_blocks.xml

出现Mojoco窗口, 9-收吊绳

Groot/gear_sonic_deploy 文件夹下启动sonic
MUSA_VISIBLE_DEVICES=4 ./target/release/g1_deploy_onnx_ref   lo   policy/release/model_decoder.onnx   reference/ardy/   --obs-config policy/release/observation_config.yaml   --encoder-file policy/release/model_encoder.onnx   --input-type keyboard   --policy-precision 32   --disable-crc-check   --enable-csv-logs   --logs-dir ./logs/baseline

Init Done, ']' 键 sonic 接管， 可以站立

本机terminal中
n-选动作
t-开始播放
r-回到第一帧

6080远程桌面terminal关闭，sonic控制器自动停下


## 目前 ardy2sonic的问题

目前的问题：ARDY 当前的 G1 模型不生成手指动作，所以grasp动作也只有伸出手臂，输入一次 prompt，身体和手指一起动这个问题需要解决。




## 手动控制sonic
跑起来 VNC 和 sonic 控制器
cd /workspace/group2/workspace/fuyuhan/GR00T-WholeBodyControl

DISPLAY=:1 python gear_sonic/scripts/run_sim_loop.py \
  --interface lo \
  --scene-path gear_sonic/data/robot_model/model_data/g1/scene_43dof_blocks.xml


cd /workspace/group2/workspace/fuyuhan/GR00T-WholeBodyControl/gear_sonic_deploy

MUSA_VISIBLE_DEVICES=4 CUDA_VISIBLE_DEVICES=4 \
./target/release/g1_deploy_onnx_ref \
  lo \
  policy/release/model_decoder.onnx \
  reference/ardy/ \
  --obs-config policy/release/observation_config.yaml \
  --encoder-file policy/release/model_encoder.onnx \
  --input-type keyboard \
  --policy-precision 32 \
  --disable-crc-check
然后


| 按键 | 功能 |
|---|---|
| `]` | 启动控制 |
| `u` | 右手闭合 |
| `y` | 右手张开 |
| `k` | 左手闭合 |
| `m` | 左手张开 |
| `o` | 停止控制并退出 |
