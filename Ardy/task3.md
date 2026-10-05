# ARDY G1：摩尔线程环境安装与离线运行

**执行位置：本文所有终端命令都在由 `registry.mthreads.com/presale/devtech/vllm-mt:d0930` 镜像启动的个人容器内执行**，包括创建虚拟环境、安装依赖、下载模型、修改配置和源码、生成动作及启动播放器。

先通过 VSCode 附加到该容器，或使用 `docker exec` 进入容器终端，再按下文操作。`/workspace/ardy-work/ardy` 是容器内的示例工作目录。镜像已有 `torch / torch_musa 2.9.0` 和 MUSA SDK，ARDY 使用已拉取的最新代码；本流程尚未在该镜像上完成实际推理验证。

## 1. 准备环境

进入已有仓库，限制使用物理 GPU 4–7：

```bash
cd /workspace/ardy-work/ardy
export MUSA_VISIBLE_DEVICES=4,5,6,7
```

若容器已将物理 4–7 重新映射为 0–3，改用 `MUSA_VISIBLE_DEVICES=0,1,2,3`。以容器启动配置为准，后文 `musa:0` 表示当前可见的第一张卡。

创建个人环境，继承镜像中的厂商 PyTorch：

```bash
python -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip 'setuptools>=61,<81' wheel
python -c "import torch, torch_musa; print(torch.__version__, torch_musa.__version__, torch.musa.is_available())"
```

最后一项应为 `True`。保存厂商版本约束，避免依赖安装替换 torch：

```bash
python - <<'PY'
from importlib.metadata import version
from pathlib import Path
lines = [f'{name}=={version(name)}' for name in ('torch', 'torch_musa')]
lines += ['numpy>=1.23,<2', 'transformers==5.8.1']
Path('constraints-musa.txt').write_text('\n'.join(lines) + '\n')
PY
```

## 2. 安装依赖

### 2.1 MUSA 版 torchvision

[ARDY README](https://github.com/nv-tlabs/ardy#setup)要求先安装 torch、torchvision。保留镜像中的 torch；torchvision 按 [torch_musa 2.9.0 README](https://github.com/MooreThreads/torch_musa/blob/v2.9.0/README.md#torchvision)从 `MooreThreads/vision` 的 `v0.22.1-musa` 分支安装。镜像已有可用的 MUSA 版时跳过。

```bash
python -m pip install -c constraints-musa.txt \
  'numpy>=1.23,<2' 'pillow>=9' ninja

export MUSA_HOME="${MUSA_HOME:-/usr/local/musa}"
export PATH="$MUSA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$MUSA_HOME/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

mkdir -p third_party
git clone --depth 1 --branch v0.22.1-musa \
  https://github.com/MooreThreads/vision.git third_party/vision-musa
(
  cd third_party/vision-musa
  MAX_JOBS=4 python setup.py install
)

python -c "import torch, torch_musa, torchvision; print(torchvision.__version__, torchvision.__file__)"
```

在已激活的个人 `.venv` 中运行官方的 `setup.py install`。构建需要镜像中的 `mcc` 和 C++ 编译器，日志应包含 `Building MUSA _C extension`。

### 2.2 ARDY 与下载工具

直接安装即可，已经安装成功的环境不用重装：

```bash
python -m pip install -c constraints-musa.txt -e '.[demo]'
python -m pip install -c constraints-musa.txt modelscope torchada
```

`.[demo]` 包含推理和浏览器回放依赖。不使用包含 NVIDIA TensorRT 的 `.[all]`。

## 3. 从 ModelScope 下载模型

**使用 ModelScope 是因为开发机可能连不上 Hugging Face，或 HF 账号尚未获得 Llama 模型访问权限。**本流程从 ModelScope 上可访问的镜像下载四份模型，运行时直接读取本地文件。

| 用途 | ModelScope 仓库 |
| --- | --- |
| ARDY G1 | [nv-community/ARDY-G1-RP-25FPS-Horizon52](https://modelscope.cn/models/nv-community/ARDY-G1-RP-25FPS-Horizon52) |
| Llama 3 8B Instruct | [LLM-Research/Meta-Llama-3-8B-Instruct](https://modelscope.cn/models/LLM-Research/Meta-Llama-3-8B-Instruct) |
| MNTP 适配器 | [oneyoungmean/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp](https://modelscope.cn/models/oneyoungmean/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp) |
| Supervised 适配器 | [oneyoungmean/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised](https://modelscope.cn/models/oneyoungmean/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised) |

在 ARDY 根目录保存并运行下载脚本：

```bash
cat > download_modelscope.py <<'PY'
from modelscope import snapshot_download

snapshot_download(
    'nv-community/ARDY-G1-RP-25FPS-Horizon52',
    local_dir='./checkpoints/ARDY-G1-RP-25FPS-Horizon52',
)
snapshot_download(
    'LLM-Research/Meta-Llama-3-8B-Instruct',
    local_dir='./text_encoders/meta-llama/Meta-Llama-3-8B-Instruct',
    ignore_file_pattern=['original/*'],
)
snapshot_download(
    'oneyoungmean/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp',
    local_dir='./text_encoders/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp',
)
snapshot_download(
    'oneyoungmean/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised',
    local_dir='./text_encoders/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised',
)
PY
MODELSCOPE_CACHE="$PWD/.modelscope-cache" python download_modelscope.py
```

合计约 17 GB。排除 `original/` 可避免重复下载原始 Llama 权重。保留本地 `McGill-NLP` 目录名，这是 ARDY 预设的加载路径；这些 ModelScope 仓库是模型镜像。

## 4. 配置本地加载

以下修改均在**开发机的 ARDY 根目录**进行。最新源码若已包含对应修正，跳过该项。

### 4.1 适配器指向本地 Llama

修改两个 `adapter_config.json` 的 `base_model_name_or_path`：

```bash
python - <<'PY'
import json
from pathlib import Path
root = Path('text_encoders').resolve()
llama = str(root / 'meta-llama/Meta-Llama-3-8B-Instruct')
for name in (
    'LLM2Vec-Meta-Llama-3-8B-Instruct-mntp',
    'LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised',
):
    path = root / 'McGill-NLP' / name / 'adapter_config.json'
    config = json.loads(path.read_text())
    config['base_model_name_or_path'] = llama
    path.write_text(json.dumps(config, indent=2) + '\n')
PY
```

目录移动后重做这一步。保留 MNTP `config.json` 的 `_name_or_path`，ARDY 用它选择 Llama 文本格式。

### 4.2 明确加载基础模型，再加载两份适配器

MNTP 只有适配器权重，却带有 `config.json`，Transformers 5.8.1 可能把它当成完整模型目录。因此仅改 JSON 不够。

在 `ardy/model/llm2vec/llm2vec.py` 的 `from_pretrained()` 中，将：

```python
model = model_class.from_pretrained(base_model_name_or_path, **kwargs)
```

替换为以下代码，保持原函数缩进：

```python
adapter_config_path = os.path.join(base_model_name_or_path, 'adapter_config.json')
has_local_adapter = os.path.isfile(adapter_config_path)
model_path = base_model_name_or_path
if has_local_adapter:
    with open(adapter_config_path) as f:
        model_path = json.load(f)['base_model_name_or_path']
model = model_class.from_pretrained(model_path, **kwargs)
```

再将原有 MNTP 加载块的条件 `if hasattr(model, "peft_config"):` 改成：

```python
if has_local_adapter or hasattr(model, 'peft_config'):
    model = PeftModel.from_pretrained(model, base_model_name_or_path)
    model = model.merge_and_unload()
```

保留后面的 supervised 适配器加载代码，以及原有 `_name_or_path` 恢复代码。完整顺序是：**本地 Llama → 合并 MNTP → 加载 supervised**。

### 4.3 使用 MUSA 设备

在 `scripts/generate.py` 的 `import torch` 前加入：

```python
import torchada
```

将 `main()` 中原先根据 `torch.cuda.is_available()` 选择设备的赋值改为：

```python
device = 'musa:0'
```

torchada 处理剩余 CUDA API 调用；它不重定向 `torch.cuda.is_available()`，所以需要显式选择 MUSA。

## 5. 离线生成

在开发机 ARDY 根目录保存环境配置：

```bash
cat > env_ardy.sh <<'SH'
source .venv/bin/activate
export CHECKPOINTS_DIR="$PWD/checkpoints"
export TEXT_ENCODERS_DIR="$PWD/text_encoders"
export TEXT_ENCODER_MODE=local
export TEXT_ENCODER_DEVICE=musa:0
export HF_HOME="$PWD/.hf-cache"
export HF_HUB_CACHE="$HF_HOME/hub"
export HUGGINGFACE_CACHE_DIR="$HF_HUB_CACHE"
export TORCH_EXTENSIONS_DIR="$PWD/.torch-extensions"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
SH
source env_ardy.sh

python scripts/generate.py 'A person walks in a circle.' \
  --model g1 \
  --checkpoints_dir ./checkpoints \
  --duration 5 \
  --seed 0 \
  --output baseline_g1
```

新终端重新设置第 1 节的 GPU 可见范围，再 `source env_ardy.sh`。`local` 模式直接加载文本编码器；离线变量禁止从 HF 补取文件，开发机无需执行 `hf auth login`。

成功时应显示 `Using device: musa:0`，并产生：

| 输出 | 内容 |
| --- | --- |
| `outputs/baseline_g1.npz` | 5 秒、25 FPS 的 G1 动作，供播放器读取 |
| `outputs/baseline_g1.csv` | MuJoCo qpos：根平移、`wxyz` 四元数和 29 个关节角（弧度），无表头 |

## 6. 查看结果

在同一个容器内启动播放器：

```bash
python scripts/visualize.py outputs/baseline_g1.npz --port 2334
```

容器终端保持运行。播放器监听 `0.0.0.0:2334`，浏览器在 Mac 上打开：

- VSCode 连接到容器时，在 **Ports / 端口** 面板转发 `2334`，Mac 浏览器打开 `http://localhost:2334`。
- VSCode 只连接宿主机时，容器还需发布端口，例如创建个人容器时添加 `-p 127.0.0.1:2334:2334`，再转发宿主机端口；也可直接将 VSCode 附加到容器。
- 若开发机端口可直接访问，打开 `http://开发机IP:2334`。

页面支持循环播放、暂停、拖动帧和切换网格 / 骨架。这是生成动作的回放，SONIC 控制和 MuJoCo 物理仿真需另外接入。
