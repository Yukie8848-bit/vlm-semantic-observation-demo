# SAM2 物体描述与点云关联教程

## 这段代码能做什么

它会对 SAM2 分割出的每个物体调用一次 VLM，输出：

- 物品名称和类别；
- 可见外观、状态和可交互部位；
- 遮挡、置信度和不确定性；
- SAM2 label、track ID 和图像二维位置；
- 可选的 PCD 点云文件路径。

需要注意：VLM 看的是 RGB、SAM2 高亮图和物体裁剪图。当前代码只把 PCD
路径关联到同一个物体结果中，**不会读取 PCD 并计算三维中心、尺寸或形状**。

## 在哪里运行

推荐在机器人视觉端运行：

```text
账号：gr3-torso-vision
位置：12号车或13号车的9号视觉端口
终端：新终端
```

这一步不调用 ROS，也不移动机器人。

## 1. 准备代码和环境

```bash
cd /home/gr3-torso-vision
git clone https://github.com/Yukie8848-bit/vlm-semantic-observation-demo.git
cd vlm-semantic-observation-demo

python3 -m pip install --user -r requirements.txt
cp .env.example .env
```

在 `.env` 中填写可用的视觉模型接口：

```text
VLM_API_STYLE=openai
API_KEY=<API Key>
BASE_URL=<VLM接口地址>
MODEL_NAME=<视觉模型名称>
```

不要把 `.env` 提交到 Git。

## 2. 准备输入

每一帧必须有三个同名文件：

```text
rgb/<frame_id>.png
sam2/<frame_id>.json
sam2/<frame_id>_labels.png
```

例如任务目录为：

```text
/home/gr3-torso-vision/videos/Switch001/
```

先设置路径：

```bash
TASK_DIR=/home/gr3-torso-vision/videos/Switch001
RGB_DIR="$TASK_DIR/rgb"
SAM2_DIR="$TASK_DIR/sam2"
OUT_DIR="$TASK_DIR/vlm_descriptions"
```

如果实际 SAM2 输出目录不是 `$TASK_DIR/sam2`，把 `SAM2_DIR` 改成真实目录。

## 3. 只生成物体描述

```bash
python3 scripts/run_sam2_vlm_task.py \
  --task-id Switch001 \
  --rgb-dir "$RGB_DIR" \
  --sam2-dir "$SAM2_DIR" \
  --output-dir "$OUT_DIR"
```

## 4. 同时关联 PCD 点云

先建立映射文件：

```bash
nano "$TASK_DIR/pointcloud_map.json"
```

示例：

```json
{
  "wall_switch:7": "semantic_pointclouds/object_0001.pcd",
  "refrigerator:2": "semantic_pointclouds/object_0002.pcd"
}
```

键的格式是：

```text
<SAM2 label>:<SAM2 track_id>
```

SAM2 `track_id` 和语义点云 `object_id` 不是同一个编号，必须人工或由上游程序确认对应关系，不能按编号猜测。

然后运行：

```bash
python3 scripts/run_sam2_vlm_task.py \
  --task-id Switch001 \
  --rgb-dir "$RGB_DIR" \
  --sam2-dir "$SAM2_DIR" \
  --pointcloud-map "$TASK_DIR/pointcloud_map.json" \
  --output-dir "$OUT_DIR"
```

如果输出目录已经有文件，请使用新的输出目录。确认需要覆盖时才增加
`--overwrite`。

## 5. 去哪里看结果

```text
Switch001/vlm_descriptions/
  task_summary.json
  acceptance_report.json
  evidence/
  objects/
  failures/
```

每个物体对应一个 JSON：

```bash
find "$OUT_DIR/objects" -maxdepth 1 -type f -name "*.json"
python3 -m json.tool "$OUT_DIR/objects/wall_switch_track_7.json"
```

重点字段：

```json
{
  "position_scope": "image_2d_only",
  "pointcloud_path": "/path/to/object_0001.pcd",
  "description": {
    "object_name": "墙面开关",
    "category": "wall_switch",
    "visual_description": "白色矩形开关面板",
    "visible_state": "无法判断",
    "interaction_parts": ["开关按键"],
    "confidence": 0.88
  }
}
```

检查整批任务是否成功：

```bash
python3 -m json.tool "$OUT_DIR/acceptance_report.json"
```

如果某个物体失败，查看：

```text
$OUT_DIR/failures/<label>_track_<id>.json
```

## 6. 当前没有实现的功能

以下功能需要后续增加 PCD 几何分析模块：

- 点云三维中心和地图坐标；
- 长、宽、高和真实距离；
- 点云形状、朝向和表面法向；
- 基于三维信息判断机械臂是否可达。

因此交付时应称为“SAM2 分割物体的 VLM 描述，并可关联对应点云文件”，不要称为“VLM 已直接理解点云”。
