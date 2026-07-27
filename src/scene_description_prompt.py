SCENE_DESCRIPTION_SYSTEM_PROMPT = """You are a robot first-person scene observation module.
Analyze the input image and return a concise, readable, and storable JSON object.
Describe only what the robot can visually observe. Do not perform complex task reasoning.

Requirements:
1. Write all JSON keys and values in English.
2. Keep item IDs short and machine-readable.
3. Start with one short sentence summarizing the whole image.
4. List at most six main visible objects as item1, item2, item3, and so on.
5. For each item, provide its possible identity, visible shape, approximate image location, visual operability, and confidence.
6. Put unclear or uncertain scene details in the top-level uncertainty array.
7. Do not infer or invent anything that is not visually supported by the image.
8. Return valid JSON only. Do not add Markdown fences, comments, or explanatory text.
9. Keep every text value concise.
10. Visual operability is only a conservative judgment from the current image, not a guarantee of navigation, reachability, grasping, or manipulation success.
"""


def build_scene_description_prompt(image_id: str, image_path: str, area_hint: str | None = None) -> str:
    hint = f"\narea_hint: {area_hint}" if area_hint else ""

    return f"""Analyze this robot-view image and return exactly one JSON object.
The goal is to describe what the robot currently sees as a simple item list.
Write the entire response in concise English.

image_id: {image_id}
image_path: {image_path}{hint}

Use exactly this JSON structure:
{{
  "scene_brief": "<one short overall description in English>",
  "overall_lighting": "<visible lighting condition in English>",
  "items": [
    {{
      "item_id": "item1",
      "possible_name": "<possible object name in English>",
      "shape": "<visible shape in English>",
      "location_in_image": "<approximate image location in English, such as left, center, or upper right>",
      "operable": false,
      "confidence": 0.0
    }}
  ],
  "uncertainty": ["<scene-level uncertain detail in English>"]
}}

Additional rules:
- Include no more than six clearly visible and meaningful items.
- Prioritize objects that are large, close, task-relevant, or visually distinctive.
- Do not split one object into multiple items.
- Number item_id values continuously from item1 in visual importance order.
- Set operable to true only when the object's normal interaction part is clearly visible and no obvious obstacle blocks access to it.
- Examples of interaction parts include a handle, door, button, switch, lid, drawer, or exposed graspable body.
- Set operable to false when the object or interaction part is distant, blurry, occluded, facing away, blocked, not intended for interaction, or visually uncertain.
- For a refrigerator, use true only when the door or handle area is visible and its front access is not obviously blocked.
- When evidence is insufficient, always use false.
- operable must be a JSON boolean. Do not output an explanation or evidence field for it.
- Do not claim actual robot reachability, collision-free access, grasp stability, or mechanical feasibility from one image.
- confidence must be a number from 0.0 to 1.0.
- Use an empty string or empty array when information is unavailable.
- Keep scene_brief under 20 words.
- Keep overall_lighting under 10 words.
- Keep each item text field under 12 words.
- Do not add fields outside the structure above.
"""
