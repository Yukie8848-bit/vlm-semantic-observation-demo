SCENE_DESCRIPTION_SYSTEM_PROMPT = """你是机器人第一视角场景语义描述模块。
请根据输入图像输出用于语义地图、任务理解和人机沟通的结构化 JSON。
重点关注：
1. 机器人当前能看到什么；
2. 画面所在区域或场景类型；
3. 主要对象、对象状态和大致位置；
4. 对象之间的空间关系；
5. 当前灯光、可通行区域、遮挡和视角限制；
6. 可能与机器人任务相关的线索，例如可整理物、可操作物、障碍物、风险或异常；
7. 不确定的地方必须写入 uncertainty；
8. 不要编造看不见的内容；
9. 只输出 JSON，不要输出解释文字。
"""


def build_scene_description_prompt(image_id: str, image_path: str, area_hint: str | None = None) -> str:
    hint = f"\narea_hint: {area_hint}" if area_hint else ""
    return f"""请分析这张机器人视角图像，并严格输出一个 JSON 对象。
任务目标：描述机器人当前看见了什么，并生成可存储、可检索的场景语义观测。

image_id: {image_id}
image_path: {image_path}{hint}

JSON schema:
{{
  "image_id": "{image_id}",
  "image_path": "{image_path}",
  "timestamp": null,
  "area_hint": {f'"{area_hint}"' if area_hint else "null"},
  "robot_view_summary": "用一两句话说明机器人当前视角能看到什么",
  "scene_type": "会议室/办公室/调试区/工具区/货架区/走廊/门口/未知",
  "visible_area": "机器人视角覆盖的区域，例如门口附近、房间左侧、工作台前方",
  "lighting": {{
    "condition": "bright/dim/dark/uncertain",
    "visible_light_sources": ["天花板灯", "窗外自然光"],
    "description": "画面整体光照情况及可见光源说明"
  }},
  "main_objects": [
    {{
      "name": "墙面开关",
      "category": "light_switch",
      "location_description": "画面左侧墙面",
      "state": "可见，但具体开关状态无法判断",
      "attributes": ["固定", "可操作"],
      "task_relevance": "可能与关灯任务相关",
      "confidence": 0.82
    }}
  ],
  "spatial_layout": [
    "墙面开关位于画面左侧",
    "纸箱位于右侧房间地面",
    "通道从画面中部通向右侧区域"
  ],
  "navigability": {{
    "free_space_description": "机器人前方可通行区域的大致情况",
    "obstacles": ["纸箱", "门框"],
    "passage_risk": "none/low/medium/high/uncertain"
  }},
  "task_relevant_observations": [
    {{
      "type": "可操作物/待整理物/通行风险/安全风险/环境状态/未知",
      "description": "墙面开关可见，可能可用于关灯任务",
      "suggested_follow_up": "靠近后确认开关状态或控制关系",
      "confidence": 0.75
    }}
  ],
  "occlusions_or_blind_spots": [
    "门框遮挡了右侧区域的一部分",
    "开关面板角度较斜，无法确认具体拨动方向"
  ],
  "uncertainty": [
    "无法确认开关控制哪一路灯",
    "无法确认部分物体是否会影响机器人通行"
  ]
}}
"""
