import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from core import analysis, llm, prompts

MIN_QUESTIONS, MAX_QUESTIONS = 3, 5


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Interview:
    topic: str
    num_questions: int = 5
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    started_at: str = field(default_factory=_now)
    finished_at: str | None = None
    plan: dict | None = None
    turns: list[dict] = field(default_factory=list)# [{"question": str, "answer": str}]
    summary: dict | None = None
    analysis: dict | None = None
    current_question: str | None = None

    def __post_init__(self):
        self.topic = self.topic.strip()
        if not self.topic:
            raise ValueError("Topic cannot be empty.")
        if not MIN_QUESTIONS <= self.num_questions <= MAX_QUESTIONS:
            raise ValueError(f"Number of questions must be {MIN_QUESTIONS}-{MAX_QUESTIONS}.")

    #public API

    @property
    def is_complete(self) -> bool:
        return len(self.turns) >= self.num_questions

    def start(self) -> str:
        """Plan the interview and return the first question."""
        self.plan = self._make_plan()
        self.current_question = self._ask_next()
        return self.current_question

    def answer(self, text: str) -> str | None:
        """Record an answer. Returns the next question, or None when the interview is done."""
        if self.current_question is None:
            raise RuntimeError("No pending question. Call start() first.")
        text = text.strip()
        if not text:
            raise ValueError("Answer cannot be empty.")

        self.turns.append({"question": self.current_question, "answer": text})
        self.current_question = None 
        if not self.is_complete:
            self.current_question = self._ask_next()
        return self.current_question

    def summarize(self) -> dict:
        """Analyze the answered turns (works for partial interviews too)."""
        if not self.turns:
            raise RuntimeError("Nothing to summarize yet.")
        summary = llm.generate_json(
            prompts.ANALYST_SYSTEM, prompts.analyst_prompt(self.topic, self.turns)
        )
        if not isinstance(summary, dict):
            summary = {}

     
        answers = [t["answer"] for t in self.turns]
        summary["notable_quotes"], removed = analysis.verify_quotes(
            summary.get("notable_quotes"), answers
        )

        self.summary = summary
        self.analysis = analysis.analyze(answers, summary, removed)
        self.finished_at = _now()
        return self.summary

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("current_question")
        data["completed"] = self.is_complete
        return data

    #internals

    def _make_plan(self) -> dict:
        raw = llm.generate_json(
            prompts.PLANNER_SYSTEM, prompts.planner_prompt(self.topic, self.num_questions)
        )
        if not isinstance(raw, dict):
            raw = {}
        goal = raw.get("goal")
        if not isinstance(goal, str) or not goal.strip():
            goal = f"Understand the participant's experiences and views on {self.topic}."
        themes = [t for t in raw.get("themes", []) if isinstance(t, str) and t.strip()]
        return {"goal": goal, "themes": themes or [self.topic]}

    def _messages(self) -> list[dict]:
        """Rebuild the conversation from turns: questions are 'assistant', answers 'user'."""
        messages = [{"role": "user", "content": prompts.KICKOFF_MESSAGE}]
        for t in self.turns:
            messages.append({"role": "assistant", "content": t["question"]})
            messages.append({"role": "user", "content": t["answer"]})
        return messages

    def _ask_next(self) -> str:
        system = prompts.interviewer_system(
            topic=self.topic,
            goal=self.plan["goal"],
            themes=self.plan["themes"],
            question_number=len(self.turns) + 1,
            total=self.num_questions,
        )
        return llm.chat(system, self._messages())


if __name__ == "__main__":
    import json

    iv = Interview(topic=input("Topic: "), num_questions=3)
    q = iv.start()
    print("Plan:", json.dumps(iv.plan, indent=2, ensure_ascii=False))
    while q:
        q = iv.answer(input(f"\n{q}\n> "))
    print(json.dumps(iv.summarize(), indent=2, ensure_ascii=False))