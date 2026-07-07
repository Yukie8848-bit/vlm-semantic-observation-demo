# VLM Semantic Observation Demo

这个 demo 用于验证机器人关灯巡检/公司场景服务机器人的第一阶段最小闭环：

本地图像输入 -> 调用公司 VLM API -> 输出结构化 JSON -> 保存本地 JSON/SQLite -> 支持简单语义查询 -> 返回原图路径和语义观测结果。

它只负责 VLM 语义观测模块，重点说明机器人视角能看到什么、当前灯光状况如何、灯是否可能开启、开关是否可见、开关状态是否可判断，以及是否需要关灯。不做本地大 VLM 部署、3DGS、SLAM、机械臂控制、实时视频流或复杂 Web 前端。

## 一键准备环境

如果你已经安装了 Miniforge/conda，推荐直接运行：

```bash
cd vlm_semantic_observation_demo
bash scripts/setup_env.sh --backend conda
```

脚本会创建默认环境 `vlm-semobs`，安装 `requirements.txt`，并在缺少 `.env` 时从 `.env.example` 复制一份。

以后进入环境：

```bash
conda activate vlm-semobs
cd vlm_semantic_observation_demo
```

也可以自定义环境名和 Python 版本：

```bash
bash scripts/setup_env.sh --backend conda --name vlm-semobs --python 3.10
```

如果没有 conda，脚本会在 `--backend auto` 下尝试使用 `.venv`：

```bash
bash scripts/setup_env.sh
```

## 手动安装依赖

```bash
cd vlm_semantic_observation_demo
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

如果系统提示缺少 `ensurepip` 或 `python3-venv`，先安装对应的 Python venv 支持包，或直接在已有 Python 环境中执行 `python3 -m pip install -r requirements.txt`。

## 配置 API

```bash
cp .env.example .env
```

编辑 `.env`：

- `VLM_API_STYLE=openai`：用于 OpenAI-compatible 的公司 VLM API。
- `API_KEY`：公司 API key。
- `BASE_URL`：OpenAI-compatible base URL，例如 `https://api.example.com/v1`。
- `MODEL_NAME`：公司提供的 VLM 模型名。
- `VLM_API_STYLE=requests`：用于普通 HTTP POST 接口，并配置 `VLM_ENDPOINT`。

`requests` 模式默认发送：

```json
{
  "model": "MODEL_NAME",
  "prompt": "系统提示词 + 用户提示词",
  "image": "data:image/jpeg;base64,...",
  "temperature": 0
}
```

如果公司接口字段不同，只需要改 `src/vlm_client.py` 里的 `_call_requests_api`。

## 放入图片

把 20 到 50 张室内关键帧图片放入：

```text
data/images/
```

支持 `.jpg`、`.jpeg`、`.png`、`.bmp`、`.webp`。

## 批量调用 VLM API

```bash
python3 scripts/run_vlm_api.py
```

可选参数：

```bash
python3 scripts/run_vlm_api.py --area-hint 会议室
python3 scripts/run_vlm_api.py --overwrite
```

如果使用仓库内公开示例数据 `data/images/switch_01/`，可以这样跑：

```bash
python3 scripts/run_vlm_api.py --image-dir data/images/switch_01 --output-dir outputs/json_switch_01 --area-hint 开关面板
```

对应构建 SQLite：

```bash
python3 scripts/build_sqlite.py --json-dir outputs/json_switch_01 --db-path outputs/switch_01.sqlite
```

对应查询：

```bash
python3 scripts/search_demo.py --db-path outputs/switch_01.sqlite --switch-visible
python3 scripts/search_demo.py --db-path outputs/switch_01.sqlite --need-action
python3 scripts/search_demo.py --db-path outputs/switch_01.sqlite --task light_off
```

脚本会：

- 遍历 `data/images/`；
- 跳过已生成的 `outputs/json/img_xxx.json`；
- 调用 VLM API；
- 尝试解析 JSON；
- 用 Pydantic 校验 schema；
- 输出机器人视角说明字段 `robot_view`；
- 输出关灯巡检字段 `light_inspection`；
- 失败时保存 `outputs/json/img_xxx.failed.json`，其中包含错误信息和 raw response。

## 构建 SQLite

```bash
python3 scripts/build_sqlite.py
```

默认生成：

```text
outputs/semantic_observations.sqlite
```

SQLite 表包括：

- `images`
- `robot_view`
- `objects`
- `light_inspection`
- `switches`
- `abnormalities`
- `relations`
- `uncertainty`

## 查询

```bash
python3 scripts/search_demo.py --keyword 线缆
python3 scripts/search_demo.py --risk medium
python3 scripts/search_demo.py --area 会议室
python3 scripts/search_demo.py --abnormal
python3 scripts/search_demo.py --uncertain
python3 scripts/search_demo.py --light-on
python3 scripts/search_demo.py --switch-visible
python3 scripts/search_demo.py --need-action
python3 scripts/search_demo.py --task light_off
```

查询结果会输出匹配到的：

- `image_path`
- `area_type`
- `scene_summary`
- `robot_view`
- `light_inspection`
- `objects`
- `abnormalities`
- `uncertainty`

其中 `image_path` 是后续回看证据图的入口。

## 结构化 JSON

核心输出不是普通 caption，而是用于语义地图存储的关灯巡检语义观测：

```json
{
  "image_id": "img_001",
  "image_path": "data/images/img_001.jpg",
  "timestamp": null,
  "area_hint": null,
  "scene_summary": "画面整体描述",
  "area_type": "会议室/调试区/工具区/货架区/走廊/未知",
  "robot_view": {
    "visible_summary": "机器人视角能看到左侧墙面开关、右侧室内区域、天花板灯和地面纸箱",
    "visible_area": "门口附近",
    "key_visible_elements": ["墙面开关", "天花板灯", "纸箱", "门框"],
    "lighting_condition_description": "画面整体较亮，右侧区域可见天花板灯发光，同时可能存在窗外自然光",
    "occlusions_or_blind_spots": ["开关拨动方向不清晰", "右侧区域部分被门框遮挡"],
    "image_quality": "清晰",
    "robot_view_limitation": "只能根据当前单帧图像判断，无法确认开关控制哪一路灯"
  },
  "objects": [
    {
      "name": "墙面开关",
      "category": "light_switch",
      "location_description": "门口右侧墙面",
      "state": "疑似开启",
      "attributes": ["固定", "可操作", "关灯任务相关"],
      "inspection_relevance": "关灯巡检任务相关",
      "risk_level": "none",
      "suggested_action": "靠近开关进一步确认或执行关灯",
      "confidence": 0.72
    }
  ],
  "light_inspection": {
    "room_lighting_state": "on",
    "ambient_light_level": "bright",
    "visible_light_sources": ["天花板灯"],
    "switch_visibility": "visible",
    "switches": [
      {
        "visible": true,
        "location_description": "门口右侧墙面",
        "state": "uncertain",
        "evidence": "开关面板可见，但拨动方向不清晰",
        "confidence": 0.65
      }
    ],
    "need_turn_off": "uncertain",
    "evidence": "房间明亮且可见天花板灯发光，但无法排除自然光影响",
    "suggested_action": "靠近开关或结合时间/自然光信息进一步确认",
    "confidence": 0.7
  },
  "spatial_relations": ["墙面开关位于门口右侧"],
  "abnormalities": [],
  "uncertainty": ["无法确认亮度是否来自自然光", "无法确认开关拨动方向"],
  "raw_model_response": null
}
```

## 当前限制

- 不是实时系统；
- 不部署本地 VLM；
- 不做 3D 建图；
- 不做大型向量数据库；
- 不做 grounding 模型评测；
- 不保证单张图片一定能可靠判断物理开关状态，必须把看不清的开关、自然光干扰、曝光问题写入 `uncertainty`；
- 只验证关灯巡检 VLM 语义观测、结构化存储和简单检索的小闭环。

## 验收标准

- 20 张图片能批量生成 JSON；
- JSON 大部分能被 Pydantic 校验通过；
- SQLite 能正常构建；
- 能按对象、区域、风险、异常、不确定性、灯光状态、开关可见性、是否需要关灯查询；
- 查询结果返回原始图片路径，作为证据图。
