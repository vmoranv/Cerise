"""
Event contracts for the in-process message bus.
"""

from __future__ import annotations

from typing import Any, TypedDict

DIALOGUE_USER_MESSAGE = "dialogue.user_message"
DIALOGUE_ASSISTANT_RESPONSE = "dialogue.assistant_response"

EMOTION_ANALYSIS_STARTED = "emotion.analysis.started"
EMOTION_RULE_SCORED = "emotion.rule.scored"
EMOTION_ANALYSIS_COMPLETED = "emotion.analysis.completed"

CHARACTER_EMOTION_CHANGED = "character.emotion_changed"

MEMORY_RECORDED = "memory.recorded"
MEMORY_CORE_UPDATED = "memory.core.updated"
MEMORY_FACT_UPSERTED = "memory.fact.upserted"
MEMORY_HABIT_RECORDED = "memory.habit.recorded"
MEMORY_EMOTIONAL_SNAPSHOT_ATTACHED = "memory.emotional_snapshot.attached"

OPERATION_WINDOW_CONNECTED = "operation.window.connected"
OPERATION_WINDOW_DISCONNECTED = "operation.window.disconnected"
OPERATION_INPUT_PERFORMED = "operation.input.performed"
OPERATION_TEMPLATE_MATCHED = "operation.template.matched"
OPERATION_ACTION_COMPLETED = "operation.action.completed"


class DialogueUserMessagePayload(TypedDict):
    session_id: str
    content: str


def build_dialogue_user_message(session_id: str, content: str) -> DialogueUserMessagePayload:
    return {"session_id": session_id, "content": content}


class DialogueAssistantResponsePayload(TypedDict):
    session_id: str
    content: str
    model: str


def build_dialogue_assistant_response(
    session_id: str,
    content: str,
    model: str,
) -> DialogueAssistantResponsePayload:
    return {"session_id": session_id, "content": content, "model": model}


class EmotionAnalysisStartedPayload(TypedDict):
    text_length: int


def build_emotion_analysis_started(text_length: int) -> EmotionAnalysisStartedPayload:
    return {"text_length": text_length}


class EmotionRuleScoredPayload(TypedDict):
    rule: str
    scores: dict[str, float]


def build_emotion_rule_scored(rule: str, scores: dict[str, float]) -> EmotionRuleScoredPayload:
    return {"rule": rule, "scores": scores}


class EmotionAnalysisCompletedPayload(TypedDict):
    primary: str
    confidence: float
    valence: float
    arousal: float
    dominance: float
    intensity: float


def build_emotion_analysis_completed(
    *,
    primary: str,
    confidence: float,
    valence: float,
    arousal: float,
    dominance: float,
    intensity: float,
) -> EmotionAnalysisCompletedPayload:
    return {
        "primary": primary,
        "confidence": confidence,
        "valence": valence,
        "arousal": arousal,
        "dominance": dominance,
        "intensity": intensity,
    }


class CharacterEmotionChangedPayload(TypedDict):
    from_state: str
    to_state: str
    intensity: float


def build_character_emotion_changed(
    *,
    from_state: str,
    to_state: str,
    intensity: float,
) -> CharacterEmotionChangedPayload:
    return {"from_state": from_state, "to_state": to_state, "intensity": intensity}


class MemoryRecordedPayload(TypedDict):
    record_id: str
    session_id: str


def build_memory_recorded(record_id: str, session_id: str) -> MemoryRecordedPayload:
    return {"record_id": record_id, "session_id": session_id}


class MemoryCoreUpdatedPayload(TypedDict):
    profile_id: str
    summary: str
    session_id: str | None


def build_memory_core_updated(
    profile_id: str,
    summary: str,
    session_id: str | None = None,
) -> MemoryCoreUpdatedPayload:
    return {"profile_id": profile_id, "summary": summary, "session_id": session_id}


class MemoryFactUpsertedPayload(TypedDict):
    fact_id: str
    session_id: str
    subject: str
    predicate: str
    object: str


def build_memory_fact_upserted(
    fact_id: str,
    session_id: str,
    subject: str,
    predicate: str,
    object: str,
) -> MemoryFactUpsertedPayload:
    return {
        "fact_id": fact_id,
        "session_id": session_id,
        "subject": subject,
        "predicate": predicate,
        "object": object,
    }


class MemoryHabitRecordedPayload(TypedDict):
    habit_id: str
    session_id: str
    task_type: str
    instruction: str


def build_memory_habit_recorded(
    habit_id: str,
    session_id: str,
    task_type: str,
    instruction: str,
) -> MemoryHabitRecordedPayload:
    return {
        "habit_id": habit_id,
        "session_id": session_id,
        "task_type": task_type,
        "instruction": instruction,
    }


class MemoryEmotionalSnapshotAttachedPayload(TypedDict):
    record_id: str
    session_id: str
    emotion: dict[str, float]


def build_memory_emotional_snapshot_attached(
    record_id: str,
    session_id: str,
    emotion: dict[str, float],
) -> MemoryEmotionalSnapshotAttachedPayload:
    return {"record_id": record_id, "session_id": session_id, "emotion": emotion}


class OperationWindowConnectedPayload(TypedDict):
    hwnd: int
    width: int
    height: int


def build_operation_window_connected(
    hwnd: int,
    width: int,
    height: int,
) -> OperationWindowConnectedPayload:
    return {"hwnd": hwnd, "width": width, "height": height}


class OperationWindowDisconnectedPayload(TypedDict):
    hwnd: int


def build_operation_window_disconnected(hwnd: int) -> OperationWindowDisconnectedPayload:
    return {"hwnd": hwnd}


class OperationInputPerformedPayload(TypedDict):
    action: str
    hwnd: int
    params: dict[str, Any]


def build_operation_input_performed(
    action: str,
    hwnd: int,
    params: dict[str, Any],
) -> OperationInputPerformedPayload:
    return {"action": action, "hwnd": hwnd, "params": params}


class OperationTemplateMatchedPayload(TypedDict):
    template: str
    threshold: float
    box: dict[str, Any]


def build_operation_template_matched(
    template: str,
    threshold: float,
    box: dict[str, Any],
) -> OperationTemplateMatchedPayload:
    return {"template": template, "threshold": threshold, "box": box}


class OperationActionCompletedPayload(TypedDict):
    action: str
    action_type: str
    status: str
    message: str
    duration: float
    data: dict[str, Any] | None


def build_operation_action_completed(
    action: str,
    action_type: str,
    status: str,
    message: str,
    duration: float,
    data: dict[str, Any] | None = None,
) -> OperationActionCompletedPayload:
    return {
        "action": action,
        "action_type": action_type,
        "status": status,
        "message": message,
        "duration": duration,
        "data": data,
    }


EVENT_NAMES = (
    DIALOGUE_USER_MESSAGE,
    DIALOGUE_ASSISTANT_RESPONSE,
    EMOTION_ANALYSIS_STARTED,
    EMOTION_RULE_SCORED,
    EMOTION_ANALYSIS_COMPLETED,
    CHARACTER_EMOTION_CHANGED,
    MEMORY_RECORDED,
    MEMORY_CORE_UPDATED,
    MEMORY_FACT_UPSERTED,
    MEMORY_HABIT_RECORDED,
    MEMORY_EMOTIONAL_SNAPSHOT_ATTACHED,
    OPERATION_WINDOW_CONNECTED,
    OPERATION_WINDOW_DISCONNECTED,
    OPERATION_INPUT_PERFORMED,
    OPERATION_TEMPLATE_MATCHED,
    OPERATION_ACTION_COMPLETED,
)

__all__ = [
    "DIALOGUE_USER_MESSAGE",
    "DIALOGUE_ASSISTANT_RESPONSE",
    "EMOTION_ANALYSIS_STARTED",
    "EMOTION_RULE_SCORED",
    "EMOTION_ANALYSIS_COMPLETED",
    "CHARACTER_EMOTION_CHANGED",
    "MEMORY_RECORDED",
    "MEMORY_CORE_UPDATED",
    "MEMORY_FACT_UPSERTED",
    "MEMORY_HABIT_RECORDED",
    "MEMORY_EMOTIONAL_SNAPSHOT_ATTACHED",
    "OPERATION_WINDOW_CONNECTED",
    "OPERATION_WINDOW_DISCONNECTED",
    "OPERATION_INPUT_PERFORMED",
    "OPERATION_TEMPLATE_MATCHED",
    "OPERATION_ACTION_COMPLETED",
    "DialogueUserMessagePayload",
    "DialogueAssistantResponsePayload",
    "EmotionAnalysisStartedPayload",
    "EmotionRuleScoredPayload",
    "EmotionAnalysisCompletedPayload",
    "CharacterEmotionChangedPayload",
    "MemoryRecordedPayload",
    "MemoryCoreUpdatedPayload",
    "MemoryFactUpsertedPayload",
    "MemoryHabitRecordedPayload",
    "MemoryEmotionalSnapshotAttachedPayload",
    "OperationWindowConnectedPayload",
    "OperationWindowDisconnectedPayload",
    "OperationInputPerformedPayload",
    "OperationTemplateMatchedPayload",
    "OperationActionCompletedPayload",
    "build_dialogue_user_message",
    "build_dialogue_assistant_response",
    "build_emotion_analysis_started",
    "build_emotion_rule_scored",
    "build_emotion_analysis_completed",
    "build_character_emotion_changed",
    "build_memory_recorded",
    "build_memory_core_updated",
    "build_memory_fact_upserted",
    "build_memory_habit_recorded",
    "build_memory_emotional_snapshot_attached",
    "build_operation_window_connected",
    "build_operation_window_disconnected",
    "build_operation_input_performed",
    "build_operation_template_matched",
    "build_operation_action_completed",
    "EVENT_NAMES",
]
