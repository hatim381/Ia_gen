"""Facade Axe 1 : transcript -> (AppState, message). Seul point d'entree pour l'UI."""
from __future__ import annotations
from core.domain.state import AppState
from core.domain.models import Intent
from core.llm.client import LLMClient
from features.voice_navigation.intent_parser import IntentParser
from features.voice_navigation import command_router


class VoiceNavigationService:
    def __init__(self, llm: LLMClient | None = None):
        self.parser = IntentParser(llm)

    def parse(self, transcript: str) -> Intent:
        return self.parser.parse(transcript)

    def handle(self, transcript: str, state: AppState) -> tuple[AppState, str, Intent]:
        intent = self.parser.parse(transcript)
        state, message = command_router.route(intent, state)
        return state, message, intent
