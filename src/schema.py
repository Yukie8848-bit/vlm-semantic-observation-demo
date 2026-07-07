from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


RiskLevel = Literal["none", "low", "medium", "high"]
ObservationState = Literal["on", "off", "uncertain"]
DecisionState = Literal["yes", "no", "uncertain"]
VisibilityState = Literal["visible", "not_visible", "partially_visible", "uncertain"]


class ObservedObject(BaseModel):
    name: str = ""
    category: str = ""
    location_description: str = ""
    state: str = ""
    attributes: list[str] = Field(default_factory=list)
    inspection_relevance: str = ""
    risk_level: RiskLevel = "none"
    suggested_action: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class Abnormality(BaseModel):
    type: str = "未知"
    description: str = ""
    related_objects: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = "none"
    suggested_action: str = ""


class RobotView(BaseModel):
    visible_summary: str = ""
    visible_area: str = ""
    key_visible_elements: list[str] = Field(default_factory=list)
    lighting_condition_description: str = ""
    occlusions_or_blind_spots: list[str] = Field(default_factory=list)
    image_quality: str = ""
    robot_view_limitation: str = ""


class LightSwitchObservation(BaseModel):
    visible: bool = False
    location_description: str = ""
    state: ObservationState = "uncertain"
    evidence: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class LightInspection(BaseModel):
    room_lighting_state: ObservationState = "uncertain"
    ambient_light_level: Literal["bright", "dim", "dark", "uncertain"] = "uncertain"
    visible_light_sources: list[str] = Field(default_factory=list)
    switch_visibility: VisibilityState = "uncertain"
    switches: list[LightSwitchObservation] = Field(default_factory=list)
    need_turn_off: DecisionState = "uncertain"
    evidence: str = ""
    suggested_action: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SemanticObservation(BaseModel):
    image_id: str
    image_path: str
    timestamp: str | None = None
    area_hint: str | None = None
    scene_summary: str = ""
    area_type: str = "未知"
    robot_view: RobotView = Field(default_factory=RobotView)
    objects: list[ObservedObject] = Field(default_factory=list)
    light_inspection: LightInspection = Field(default_factory=LightInspection)
    spatial_relations: list[str] = Field(default_factory=list)
    abnormalities: list[Abnormality] = Field(default_factory=list)
    uncertainty: list[str] = Field(default_factory=list)
    raw_model_response: str | None = None

    @field_validator("objects", "spatial_relations", "abnormalities", "uncertainty", mode="before")
    @classmethod
    def empty_list_when_missing(cls, value):
        return [] if value is None else value
