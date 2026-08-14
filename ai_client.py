"""
ai_client.py — Unified chat client supporting:
  • Groq  (llama-3.3-70b-versatile — generous free tier)
  • Ollama (local, unlimited)
  • Mistral AI (free tier)
  • OpenAI-compatible endpoints
"""
from __future__ import annotations
import os, logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── model presets ────────────────────────────────────────────────
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]
OLLAMA_MODELS = [
    "llama3.2",
    "llama3.1",
    "mistral",
    "phi3",
    "gemma2",
    "qwen2.5",
]
MISTRAL_MODELS = [
    "mistral-small-latest",
    "open-mixtral-8x7b",
    "open-mistral-nemo",
]

INTERVIEW_SYSTEM = """You are ME — a real software architect with 6+ years of experience, currently in a live job interview.

═══════════════════════════════════════
OUTPUT FORMAT — ALWAYS FOLLOW THIS:
═══════════════════════════════════════

For CONCEPT / THEORY questions (e.g. "What is X?", "Explain Y", "Difference between A and B"):

  → One-line direct answer first (plain sentence, no label)
  • Point 1 — key idea or definition in simple words
  • Point 2 — how it actually works or what it does
  • Point 3 — when / why you use it (real scenario from my experience)
  • Point 4 — one trade-off, gotcha, or best practice I follow
  (3 to 5 points max — skip any that don't add value)

For EXPERIENCE / BEHAVIOURAL questions (e.g. "Tell me about yourself", "Describe a challenge", "What have you worked on"):

  → One opening sentence about yourself
  • Point 1 — relevant experience or project from my background
  • Point 2 — what I specifically did / my role
  • Point 3 — outcome, result, or what I learned
  • Point 4 — how it connects to this role or question
  (Use resume context if available — reference real projects and skills)

For CODE questions (e.g. "Write a function to...", "How would you implement..."):

  → First: explain your approach in 2-3 points BEFORE writing any code
  • Approach point 1 — what data structure / algorithm / pattern to use
  • Approach point 2 — why this approach (trade-offs)
  • Approach point 3 — edge cases to handle
  Then: write clean, minimal, working code with short inline comments only where needed
  Then: one point about how this could be improved or scaled

═══════════════════════════════════════
STRICT RULES:
═══════════════════════════════════════
- Each bullet point is ONE short sentence — easy to say aloud during interview
- Points should be INDEPENDENT — interviewer can ask follow-up on any single point
- First person always: "I use", "I've worked on", "In my last project", "I usually"
- NO paragraphs — if you write a paragraph you are breaking the format
- NO AI phrases: "Certainly", "Great question", "Of course", "As an AI", "I'd be happy to"
- NO markdown bold (**text**), NO headers (###), NO extra formatting — just plain • points
- Keep human tone: "honestly", "I think", "from what I've seen", "I tend to"
- If resume context is given — reference your actual projects naturally in the experience points
- For things you are not sure about: "I'm not 100% certain but I think..." as a point

═══════════════════════════════════════
EXAMPLES:
═══════════════════════════════════════

Q: What is a REST API?
So basically a REST API is a way for two systems to talk over HTTP using standard methods.
• It uses HTTP verbs — GET to fetch, POST to create, PUT to update, DELETE to remove
• Everything is stateless — each request carries all the info the server needs, no session
• I've built REST APIs in Python with FastAPI and Flask in most of my backend projects
• One thing I always do is version the API (like /v1/) so changes don't break existing clients

Q: Tell me about yourself
I'm a software architect with around 6 years in backend systems and cloud infrastructure.
• I've mainly worked on Python-based microservices and REST APIs at scale
• In my recent project I designed a data pipeline handling around 2 million records a day
• I'm strong on system design, database optimisation, and CI/CD automation
• I'm looking to move into a role where I can work more on architecture decisions at a higher level

Q: Write a function to reverse a linked list
I'd do this iteratively — simpler to reason about and O(1) space.
• Use three pointers: prev, current, next — walk through and flip each link
• Edge cases: empty list returns None, single node returns itself
• Time complexity is O(n), space is O(1) — better than recursive which uses O(n) stack
```python
def reverse_linked_list(head):
    prev, curr = None, head
    while curr:
        nxt = curr.next
        curr.next = prev
        prev = curr
        curr = nxt
    return prev
```
• This could be extended to reverse in groups of k nodes for more complex requirements
"""


class AIClient:
    def __init__(
        self,
        provider: str = "groq",
        model: str = "",
        api_key: str = "",
        ollama_url: str = "http://localhost:11434",
    ):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key or os.getenv(_env_key(self.provider), "")
        self.ollama_url = ollama_url
        self._client = None
        self._setup()

    # ── setup ────────────────────────────────────────────────────
    def _setup(self):
        if self.provider == "groq":
            self.model = self.model or GROQ_MODELS[0]
            if self.api_key:
                try:
                    from groq import Groq
                    self._client = Groq(api_key=self.api_key)
                    logger.info("Groq client ready — model: %s", self.model)
                except ImportError:
                    logger.warning("groq package not installed; pip install groq")

        elif self.provider == "ollama":
            self.model = self.model or OLLAMA_MODELS[0]
            logger.info("Ollama client ready — model: %s @ %s", self.model, self.ollama_url)

        elif self.provider == "mistral":
            self.model = self.model or MISTRAL_MODELS[0]
            if self.api_key:
                try:
                    try:
                        from mistralai.client import Mistral  # v2+
                    except ImportError:
                        from mistralai import Mistral          # v0/v1
                    self._client = Mistral(api_key=self.api_key)
                    logger.info("Mistral client ready — model: %s", self.model)
                except ImportError:
                    logger.warning("mistralai package not installed; pip install mistralai")

        elif self.provider == "openai":
            self.model = self.model or "gpt-4o-mini"
            if self.api_key:
                try:
                    from openai import OpenAI
                    self._client = OpenAI(api_key=self.api_key)
                    logger.info("OpenAI client ready — model: %s", self.model)
                except ImportError:
                    logger.warning("openai package not installed")

    # ── chat ─────────────────────────────────────────────────────
    def chat(self, question: str, context: str = "", system: str = "", resume: str = "") -> str:
        sys_msg = system or INTERVIEW_SYSTEM
        if resume:
            sys_msg += f"\n\n═══════════════════════════════════════════\nMY RESUME / BACKGROUND (use this to personalise answers):\n═══════════════════════════════════════════\n{resume}\n"

        user_msg = question
        if context:
            user_msg = f"Web search context (use naturally, don't mention 'search results'):\n{context}\n\nQuestion: {question}"

        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user",   "content": user_msg},
        ]
        try:
            if self.provider == "groq":
                return self._groq_chat(messages)
            elif self.provider == "ollama":
                return self._ollama_chat(messages)
            elif self.provider == "mistral":
                return self._mistral_chat(messages)
            elif self.provider == "openai":
                return self._openai_chat(messages)
            else:
                return "Unknown provider selected."
        except Exception as exc:
            logger.exception("AI chat error")
            return f"Error: {exc}"

    # ── providers ────────────────────────────────────────────────
    def _groq_chat(self, messages) -> str:
        if not self._client:
            return "Groq API key not set. Add GROQ_API_KEY to .env"
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=512,
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()

    def _ollama_chat(self, messages) -> str:
        import requests, json
        resp = requests.post(
            f"{self.ollama_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False,
                  "options": {"num_predict": 512, "temperature": 0.5}},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    def _mistral_chat(self, messages) -> str:
        if not self._client:
            return "Mistral API key not set. Add MISTRAL_API_KEY to .env"
        resp = self._client.chat.complete(
            model=self.model,
            messages=messages,
            max_tokens=512,
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()

    def _openai_chat(self, messages) -> str:
        if not self._client:
            return "OpenAI API key not set. Add OPENAI_API_KEY to .env"
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=512,
            temperature=0.5,
        )
        return resp.choices[0].message.content.strip()

    # ── helpers ──────────────────────────────────────────────────
    def update(self, provider: str, model: str, api_key: str = ""):
        self.provider = provider.lower()
        self.model = model
        if api_key:
            self.api_key = api_key
        self._setup()

    @staticmethod
    def models_for(provider: str) -> list[str]:
        p = provider.lower()
        if p == "groq":    return GROQ_MODELS
        if p == "ollama":  return OLLAMA_MODELS
        if p == "mistral": return MISTRAL_MODELS
        return []


def _env_key(provider: str) -> str:
    return {"groq": "GROQ_API_KEY", "mistral": "MISTRAL_API_KEY", "openai": "OPENAI_API_KEY"}.get(provider, "")
