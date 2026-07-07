SYSTEM_PROMPT = """你是机器人关灯巡检语义观测模块。
请根据输入图像输出用于语义地图存储的结构化 JSON。
重点关注：
1. 场景区域类型；
2. 从机器人视角能看到什么，包括可见区域、关键物体、遮挡和视角限制；
3. 灯光状况，包括画面整体亮度、可见光源、自然光/人工光的证据；
4. 灯是否可能亮着，画面中是否能看到发光灯具或明显照明来源；
5. 墙面开关是否可见，开关状态是否能判断；
6. 是否需要执行关灯动作；
7. 与关灯任务相关的重要对象、位置和空间关系；
8. 是否存在异常、风险或待处理事项；
9. 不确定的地方必须写入 uncertainty；
10. 不要把自然光、屏幕光或曝光偏亮直接编造成灯已开启；
11. 不要编造看不见的开关或灯具；
12. 只输出 JSON，不要输出解释文字。
"""


def build_user_prompt(image_id: str, image_path: str, area_hint: str | None = None) -> str:
    hint = f"\narea_hint: {area_hint}" if area_hint else ""
    return f"""请分析这张机器人关键帧图像，并严格输出一个 JSON 对象。
任务目标：关灯巡检。请判断灯光状态、开关可见性、开关状态，以及是否需要关灯。

image_id: {image_id}
image_path: {image_path}{hint}

JSON schema:
枚举字段只能从给定值中选择一个，不要输出带斜杠的组合字符串：
- room_lighting_state/state: "on", "off", "uncertain"
- ambient_light_level: "bright", "dim", "dark", "uncertain"
- switch_visibility: "visible", "not_visible", "partially_visible", "uncertain"
- need_turn_off: "yes", "no", "uncertain"

{{
  "image_id": "{image_id}",
  "image_path": "{image_path}",
  "timestamp": null,
  "area_hint": {f'"{area_hint}"' if area_hint else "null"},
  "scene_summary": "画面整体描述",
  "area_type": "会议室/调试区/工具区/货架区/走廊/未知",
  "robot_view": {{
    "visible_summary": "机器人视角能看到左侧墙面开关、右侧室内区域、天花板灯和地面纸箱",
    "visible_area": "门口附近/会议室入口/走廊转角/未知",
    "key_visible_elements": ["墙面开关", "天花板灯", "纸箱", "门框"],
    "lighting_condition_description": "画面整体较亮，右侧区域可见天花板灯发光，同时可能存在窗外自然光",
    "occlusions_or_blind_spots": ["开关拨动方向不清晰", "右侧区域部分被门框遮挡"],
    "image_quality": "清晰/轻微模糊/过暗/过曝/未知",
    "robot_view_limitation": "只能根据当前单帧图像判断，无法确认开关控制哪一路灯"
  }},
  "objects": [
    {{
      "name": "墙面开关",
      "category": "light_switch",
      "location_description": "门口右侧墙面",
      "state": "疑似开启/关闭/无法判断",
      "attributes": ["固定", "可操作", "关灯任务相关"],
      "inspection_relevance": "关灯巡检任务相关",
      "risk_level": "none",
      "suggested_action": "靠近开关进一步确认或执行关灯",
      "confidence": 0.72
    }}
  ],
  "light_inspection": {{
    "room_lighting_state": "on",
    "ambient_light_level": "bright",
    "visible_light_sources": ["天花板灯", "窗外自然光"],
    "switch_visibility": "visible",
    "switches": [
      {{
        "visible": true,
        "location_description": "门口右侧墙面",
        "state": "uncertain",
        "evidence": "开关面板可见，但拨动方向不清晰",
        "confidence": 0.65
      }}
    ],
    "need_turn_off": "uncertain",
    "evidence": "房间明亮且可见天花板灯发光，但无法排除自然光影响",
    "suggested_action": "如果机器人可操作墙面开关，前往门口右侧确认并关灯；否则提醒人工确认",
    "confidence": 0.7
  }},
  "spatial_relations": ["水杯位于会议桌右侧"],
  "abnormalities": [
    {{
      "type": "通行风险/杂乱/疑似遗留物/安全风险/未知",
      "description": "地面有线缆散落，可能影响机器人通行",
      "related_objects": ["线缆"],
      "risk_level": "medium",
      "suggested_action": "提醒人工整理或机器人绕行"
    }}
  ],
  "uncertainty": ["无法确认亮度是否来自自然光", "无法确认开关拨动方向"],
  "raw_model_response": null
}}
"""
