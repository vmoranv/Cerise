"""Event contract smoke tests."""

from contracts import events as ev


def test_event_names_unique() -> None:
    names = list(ev.EVENT_NAMES)
    assert len(names) == len(set(names))
    assert all(isinstance(name, str) and name for name in names)


def test_dialogue_user_message_payload() -> None:
    payload = ev.build_dialogue_user_message("session-1", "hello")
    assert payload == {"session_id": "session-1", "content": "hello"}


def test_dialogue_assistant_response_payload() -> None:
    payload = ev.build_dialogue_assistant_response("session-1", "hi", "gpt")
    assert payload == {"session_id": "session-1", "content": "hi", "model": "gpt"}


def test_emotion_analysis_started_payload() -> None:
    payload = ev.build_emotion_analysis_started(42)
    assert payload == {"text_length": 42}


def test_emotion_rule_scored_payload() -> None:
    payload = ev.build_emotion_rule_scored("rule", {"happy": 0.5})
    assert payload == {"rule": "rule", "scores": {"happy": 0.5}}


def test_emotion_analysis_completed_payload() -> None:
    payload = ev.build_emotion_analysis_completed(
        primary="happy",
        confidence=0.9,
        valence=0.1,
        arousal=0.2,
        dominance=0.3,
        intensity=0.9,
    )
    assert payload == {
        "primary": "happy",
        "confidence": 0.9,
        "valence": 0.1,
        "arousal": 0.2,
        "dominance": 0.3,
        "intensity": 0.9,
    }


def test_character_emotion_changed_payload() -> None:
    payload = ev.build_character_emotion_changed(
        from_state="neutral",
        to_state="happy",
        intensity=0.8,
    )
    assert payload == {"from_state": "neutral", "to_state": "happy", "intensity": 0.8}


def test_memory_recorded_payload() -> None:
    payload = ev.build_memory_recorded("record-1", "session-1")
    assert payload == {"record_id": "record-1", "session_id": "session-1"}


def test_memory_core_updated_payload() -> None:
    payload = ev.build_memory_core_updated("profile-1", "summary", "session-1")
    assert payload == {"profile_id": "profile-1", "summary": "summary", "session_id": "session-1"}


def test_memory_fact_upserted_payload() -> None:
    payload = ev.build_memory_fact_upserted("fact-1", "session-1", "User", "likes", "coffee")
    assert payload == {
        "fact_id": "fact-1",
        "session_id": "session-1",
        "subject": "User",
        "predicate": "likes",
        "object": "coffee",
    }


def test_memory_habit_recorded_payload() -> None:
    payload = ev.build_memory_habit_recorded("habit-1", "session-1", "coding", "use type hints")
    assert payload == {
        "habit_id": "habit-1",
        "session_id": "session-1",
        "task_type": "coding",
        "instruction": "use type hints",
    }


def test_memory_emotional_snapshot_attached_payload() -> None:
    payload = ev.build_memory_emotional_snapshot_attached("record-1", "session-1", {"joy": 0.8})
    assert payload == {"record_id": "record-1", "session_id": "session-1", "emotion": {"joy": 0.8}}
