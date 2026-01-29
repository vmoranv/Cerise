"""Proactive chat scheduling service."""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from datetime import datetime

from ...contracts.events import DIALOGUE_USER_MESSAGE
from ...infrastructure import Event, EventBus, StateStore
from .proactive_config import ProactiveChatConfig, ProactiveSessionConfig
from .proactive_state import ProactiveSessionState
from .proactive_time import is_quiet_time, next_quiet_end, parse_quiet_hours

logger = logging.getLogger(__name__)


SleepFunc = Callable[[float], Awaitable[None]]
NowFunc = Callable[[], datetime]


class ProactiveChatService:
    """Schedule proactive messages based on inactivity."""

    def __init__(
        self,
        *,
        bus: EventBus,
        dialogue_engine,
        config: ProactiveChatConfig,
        state_store: StateStore | None = None,
        now: NowFunc | None = None,
        sleep: SleepFunc | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self._bus = bus
        self._dialogue = dialogue_engine
        self._config = config
        self._state_store = state_store or StateStore(config.state_path)
        self._state_key = "proactive.sessions"
        self._lock = asyncio.Lock()
        self._tasks: dict[str, asyncio.Task] = {}
        self._now = now or datetime.now
        self._sleep = sleep or asyncio.sleep
        self._rng = rng or random.Random()
        self._timezone = None
        if config.timezone:
            try:
                import zoneinfo

                self._timezone = zoneinfo.ZoneInfo(config.timezone)
            except Exception:  # pragma: no cover - falls back to system time
                logger.warning("Invalid timezone '%s', using local time", config.timezone)
                self._timezone = None

    def attach(self) -> None:
        if not self._config.enabled:
            return
        self._bus.subscribe(DIALOGUE_USER_MESSAGE, self._handle_user_message)

    async def start(self) -> None:
        if not self._config.enabled:
            return
        await self._restore_schedules()
        await self._schedule_auto_triggers()

    async def shutdown(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()

    async def _handle_user_message(self, event: Event) -> None:
        data = event.data or {}
        session_id = data.get("session_id")
        if not session_id:
            return
        session_config = self._get_session_config(session_id)
        if not session_config:
            return
        now = self._now_time()
        async with self._lock:
            state = await self._get_state(session_id)
            state.last_user_at = now.timestamp()
            state.unanswered_count = 0
            await self._set_state(session_id, state)
        await self._schedule_next(session_id, session_config)

    async def _restore_schedules(self) -> None:
        stored = await self._load_states()
        now = self._now_time().timestamp()
        for session_id, data in stored.items():
            session_config = self._get_session_config(session_id)
            if not session_config:
                continue
            state = ProactiveSessionState.from_dict(data)
            if state.next_trigger_at and state.next_trigger_at > now:
                delay = max(state.next_trigger_at - now, 0.0)
                self._schedule_task(session_id, delay, state.next_trigger_at)

    async def _schedule_auto_triggers(self) -> None:
        config = self._config
        if not config.auto_trigger.enabled:
            return
        delay = max(config.auto_trigger.after_minutes, 0) * 60
        if delay <= 0:
            return
        for session_id in self._iter_enabled_sessions():
            state = await self._get_state(session_id)
            if state.last_user_at or state.next_trigger_at:
                continue
            trigger_at = self._now_time().timestamp() + delay
            await self._set_state(session_id, state)
            self._schedule_task(session_id, delay, trigger_at)

    async def _schedule_next(self, session_id: str, config: ProactiveSessionConfig) -> None:
        delay = self._compute_delay_seconds(config)
        if delay <= 0:
            return
        trigger_at = self._now_time().timestamp() + delay
        async with self._lock:
            state = await self._get_state(session_id)
            state.next_trigger_at = trigger_at
            await self._set_state(session_id, state)
        self._schedule_task(session_id, delay, trigger_at)

    def _schedule_task(self, session_id: str, delay: float, trigger_at: float) -> None:
        task = self._tasks.get(session_id)
        if task:
            task.cancel()
        self._tasks[session_id] = asyncio.create_task(self._run_after_delay(session_id, delay, trigger_at))

    async def _run_after_delay(self, session_id: str, delay: float, trigger_at: float) -> None:
        try:
            await self._sleep(delay)
            await self._trigger_session(session_id, trigger_at)
        except asyncio.CancelledError:
            return

    async def _trigger_session(self, session_id: str, trigger_at: float) -> None:
        session_config = self._get_session_config(session_id)
        if not session_config:
            return
        async with self._lock:
            state = await self._get_state(session_id)
            if state.next_trigger_at and abs(state.next_trigger_at - trigger_at) > 1.0:
                return
            if session_config.schedule.max_unanswered_times > 0 and state.unanswered_count >= (
                session_config.schedule.max_unanswered_times
            ):
                return

        quiet_delay = self._seconds_until_quiet_end(session_config)
        if quiet_delay:
            self._schedule_task(session_id, quiet_delay, self._now_time().timestamp() + quiet_delay)
            return

        session = self._dialogue.get_session(session_id)
        if not session:
            session = self._dialogue.create_session(session_id=session_id)

        prompt = self._build_prompt(session_config, state)
        response = await self._dialogue.proactive_chat(
            session=session,
            prompt=prompt,
            provider=session_config.provider_id or None,
            model=session_config.model or None,
            temperature=session_config.temperature,
            max_tokens=session_config.max_tokens,
        )

        if response:
            async with self._lock:
                state = await self._get_state(session_id)
                state.unanswered_count += 1
                await self._set_state(session_id, state)
            await self._schedule_next(session_id, session_config)

    def _get_session_config(self, session_id: str) -> ProactiveSessionConfig | None:
        config = self._config
        for session in config.sessions:
            if session.session_id == session_id:
                return session if session.enabled else None
        if not config.apply_to_all_sessions and session_id not in config.session_allowlist:
            return None
        return ProactiveSessionConfig(
            session_id=session_id,
            enabled=True,
            prompt=config.prompt,
            provider_id=config.provider_id,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            schedule=config.schedule,
            auto_trigger=config.auto_trigger,
        )

    def _iter_enabled_sessions(self) -> list[str]:
        config = self._config
        session_ids = {session.session_id for session in config.sessions if session.enabled}
        if config.apply_to_all_sessions:
            return list(session_ids)
        session_ids.update(config.session_allowlist)
        return list(session_ids)

    def _build_prompt(self, config: ProactiveSessionConfig, state: ProactiveSessionState) -> str:
        now = self._now_time()
        prompt = config.prompt
        prompt = prompt.replace("{{current_time}}", now.strftime("%Y-%m-%d %H:%M"))
        prompt = prompt.replace("{{unanswered_count}}", str(state.unanswered_count))
        return prompt

    def _compute_delay_seconds(self, config: ProactiveSessionConfig) -> float:
        min_seconds = max(config.schedule.min_interval_minutes, 0) * 60
        max_seconds = max(config.schedule.max_interval_minutes, 0) * 60
        if max_seconds <= 0:
            return 0.0
        if min_seconds > max_seconds:
            min_seconds = max_seconds
        return float(self._rng.randint(int(min_seconds), int(max_seconds)))

    def _seconds_until_quiet_end(self, config: ProactiveSessionConfig) -> float:
        quiet_hours = config.schedule.quiet_hours
        window = parse_quiet_hours(quiet_hours)
        if not window:
            return 0.0
        start_hour, end_hour = window
        now = self._now_time()
        if not is_quiet_time(now, start_hour, end_hour):
            return 0.0
        end_time = next_quiet_end(now, start_hour, end_hour)
        return max((end_time - now).total_seconds(), 0.0)

    def _now_time(self) -> datetime:
        if self._timezone:
            return datetime.now(self._timezone)
        return self._now()

    async def _load_states(self) -> dict[str, dict]:
        data = await self._state_store.get(self._state_key, {})
        return data if isinstance(data, dict) else {}

    async def _get_state(self, session_id: str) -> ProactiveSessionState:
        data = await self._load_states()
        session_data = data.get(session_id, {}) if isinstance(data, dict) else {}
        return ProactiveSessionState.from_dict(session_data)

    async def _set_state(self, session_id: str, state: ProactiveSessionState) -> None:
        data = await self._load_states()
        data[session_id] = state.to_dict()
        await self._state_store.set(self._state_key, data)
