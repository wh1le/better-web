"""Minimal rich-based logging. Only essential info, no noise."""
from contextlib import contextmanager

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

__all__ = ["console", "status", "progress", "info", "warn", "error", "done", "step"]

console = Console(stderr=True)


def info(msg: str):
    console.print(f"  {msg}")


def warn(msg: str):
    console.print(f"  [yellow]{msg}[/yellow]")


def error(msg: str):
    console.print(f"  [red]{msg}[/red]")


def done(msg: str):
    console.print(f"  [green]{msg}[/green]")


def step(label: str):
    console.print(f"\n  [bold dim]▸ {label}[/bold dim]")


@contextmanager
def status(msg: str):
    with console.status(msg, spinner="dots"):
        yield


@contextmanager
def progress(label: str, total: int):
    with Progress(
        TextColumn("  {task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
    ) as p:
        task = p.add_task(label, total=total)
        yield lambda n=1: p.advance(task, n)
