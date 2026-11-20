"""terminal ui"""
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from core import storage
from core.interview import MAX_QUESTIONS, MIN_QUESTIONS, Interview
from core.llm import LLMError

console = Console()

SUGGESTED_TOPICS = [
    "AI in the workplace",
    "Productivity tools",
    "Scientific research",
    "Remote work",
]

SENTIMENT_COLORS = {"positive": "green", "negative": "red", "mixed": "yellow", "neutral": "white"}


#screens

def show_welcome() -> None:
    console.print(Panel.fit(
        "[bold]AI Interviewer[/bold]\n\n"
        "A short, adaptive interview on a topic of your choice.\n"
        "The AI asks one question at a time and follows up on what you say.\n"
        "At the end you get a summary: themes, sentiment and key points.\n\n"
        "[dim]Transcripts are saved locally in transcripts/. Press Ctrl+C anytime to stop.[/dim]",
        border_style="cyan",
    ))


def ask_setup() -> tuple[str, int]:
    console.print("\n[bold]Choose a topic[/bold]: pick a number or type your own.")
    for i, topic in enumerate(SUGGESTED_TOPICS, 1):
        console.print(f"  [cyan]{i}[/cyan]. {topic}")

    while True:
        choice = Prompt.ask("\nTopic").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(SUGGESTED_TOPICS):
            topic = SUGGESTED_TOPICS[int(choice) - 1]
            break
        if choice:
            topic = choice
            break
        console.print("[yellow]Please enter a topic.[/yellow]")

    num = IntPrompt.ask(
        "Number of questions",
        choices=[str(n) for n in range(MIN_QUESTIONS, MAX_QUESTIONS + 1)],
        default=MAX_QUESTIONS,
    )
    return topic, num


def ask_answer() -> str:
    while True:
        text = Prompt.ask("[bold green]You[/bold green]").strip()
        if text:
            return text
        console.print("[yellow]Please type an answer (or press Ctrl+C to stop).[/yellow]")


#summary

def _sentiment_bar(score: float, width: int = 21) -> Text:
    #marked, scaled bar
    pos = round((score + 1) / 2 * (width - 1))
    bar = Text()
    for i in range(width):
        if i == pos:
            bar.append("●", style="bold")
        elif i == width // 2:
            bar.append("│", style="dim")
        else:
            bar.append("─", style="dim")
    return bar


def _bullets(title: str, items) -> None:
    items = [i for i in (items or []) if isinstance(i, str)]
    if items:
        console.print(f"\n[bold]{title}[/bold]")
        for item in items:
            console.print(f"  • {escape(item)}")


def show_summary(iv: Interview) -> None:
    s = iv.summary or {}
    console.print()
    console.print(Rule("[bold]Interview summary[/bold]"))
    console.print(Panel(Text(str(s.get("summary", ""))), title=escape(iv.topic), border_style="cyan"))

    # sentiment validation
    sent = s.get("sentiment") if isinstance(s.get("sentiment"), dict) else {}
    label = str(sent.get("label", "neutral")).lower()
    try:
        score = max(-1.0, min(1.0, float(sent.get("score", 0))))
    except (TypeError, ValueError):
        score = 0.0
    console.print(Text.assemble(
        ("Sentiment: ", "bold"),
        (f"{label} ({score:+.1f})   ", SENTIMENT_COLORS.get(label, "white")),
        ("negative ", "dim"), _sentiment_bar(score), (" positive", "dim"),
    ))
    if sent.get("rationale"):
        console.print(f"[dim]{escape(str(sent['rationale']))}[/dim]")
    a = iv.analysis or {}
    local = a.get("local_sentiment")
    if local:
        verdict = {True: "agrees with the AI", False: "differs from the AI", None: "no AI score to compare"}
        console.print(f"[dim]Cross-check, {local['method']}: {local['score']:+.2f} "
                      f"({verdict[local['agrees_with_ai']]})[/dim]")
    if a.get("quotes_removed"):
        console.print(f"[dim]Removed {len(a['quotes_removed'])} quote(s) not found verbatim in the answers.[/dim]")
    if a.get("stats"):
        st = a["stats"]
        console.print(f"[dim]{st['answers']} answers, {st['total_words']} words "
                      f"(avg {st['avg_words_per_answer']} per answer)[/dim]")

    themes = [t for t in (s.get("themes") or []) if isinstance(t, dict)]
    if themes:
        table = Table(title="Themes", title_justify="left", show_lines=True, expand=True)
        table.add_column("Theme", style="bold cyan", ratio=1)
        table.add_column("Description", ratio=3)
        for t in themes:
            table.add_row(escape(str(t.get("name", ""))), escape(str(t.get("description", ""))))
        console.print()
        console.print(table)

    _bullets("Key points", s.get("key_points"))

    quotes = [q for q in (s.get("notable_quotes") or []) if isinstance(q, str)]
    if quotes:
        console.print("\n[bold]Notable quotes[/bold]")
        for q in quotes:
            console.print(f'  [italic]"{escape(q)}"[/italic]')

    keywords = [k for k in (s.get("keywords") or []) if isinstance(k, str)]
    if keywords:
        console.print("\n[bold]Keywords:[/bold] " + ", ".join(f"[magenta]{escape(k)}[/magenta]" for k in keywords))


#flow

def run_interview(iv: Interview) -> None:
    with console.status("[cyan]Preparing your interview...", spinner="dots"):
        question = iv.start()

    while question:
        console.print()
        console.print(Rule(f"Question {len(iv.turns) + 1} of {iv.num_questions}", style="dim"))
        console.print(f"[bold cyan]Interviewer:[/bold cyan] {escape(question)}\n")
        answer = ask_answer()

        with console.status("[cyan]Thinking...", spinner="dots"):
            question = iv.answer(answer)
        storage.save(iv.to_dict())  # autosave after every answer


def finish(iv: Interview) -> None:
    if not iv.turns:
        console.print("[dim]No answers recorded, nothing saved.[/dim]")
        return

    try:
        with console.status("[cyan]Analyzing your answers...", spinner="dots"):
            iv.summarize()
    except (LLMError, KeyboardInterrupt):
        console.print("[yellow]Couldn't generate the summary. Transcript saved without it.[/yellow]")

    path = storage.save(iv.to_dict())
    if iv.summary:
        show_summary(iv)
    console.print(f"\n[green]Saved to[/green] {path}")


def main() -> None:
    show_welcome()
    try:
        topic, num = ask_setup()
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Bye![/dim]")
        return

    iv = Interview(topic=topic, num_questions=num)
    try:
        run_interview(iv)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interview stopped early.[/yellow]")
    except LLMError as e:
        console.print(f"\n[red]Problem talking to the AI:[/red] {e}")

    finish(iv)


if __name__ == "__main__":
    main()