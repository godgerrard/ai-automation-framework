"""
Framework CLI — developer-facing code-generation and test-execution commands.

Install entry point (after pip install -e .):
    framework <command>

Direct invocation (without install):
    python -m cli.commands <command>
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import click

from core.memory_engine import MemoryEngine
from utils.helpers import CodeGenerator, StoryParser


@click.group()
@click.version_option("1.0.0", prog_name="framework")
def framework() -> None:
    """AI-Augmented Test Automation Framework CLI."""


# ── generate-page ─────────────────────────────────────────────────────────────

@framework.command("generate-page")
@click.option("--url", required=True, help="Target page URL")
@click.option("--name", default=None, help="Override class name (derived from URL by default)")
@click.option("--output-dir", default="pages", show_default=True, help="Output directory for page class")
def generate_page(url: str, name: Optional[str], output_dir: str) -> None:
    """Generate a skeleton POM Page class and matching Locator file from a URL.

    After generation, run the MCP tool inspect_current_dom to discover real
    selectors and update the generated Locator class accordingly.
    """
    gen = CodeGenerator()
    page_name = name or _url_to_class_name(url)
    snake = _camel_to_snake(page_name)

    page_file = Path(output_dir) / f"{snake}_page.py"
    locator_file = Path("locators") / f"{snake}_locators.py"

    page_file.parent.mkdir(parents=True, exist_ok=True)
    locator_file.parent.mkdir(parents=True, exist_ok=True)

    page_file.write_text(gen.generate_page_class(page_name, url), encoding="utf-8")
    locator_file.write_text(gen.generate_locator_class(page_name), encoding="utf-8")

    click.echo(click.style(f"  [OK] {page_file}", fg="green"))
    click.echo(click.style(f"  [OK] {locator_file}", fg="green"))
    click.echo()
    click.echo(click.style("Next:", bold=True) + " run MCP tool inspect_current_dom to update selectors.")


# ── generate-test ─────────────────────────────────────────────────────────────

@framework.command("generate-test")
@click.option("--story", required=True, type=click.Path(exists=True), help="Path to user story JSON/TXT file")
@click.option("--output-dir", default="tests/workflows", show_default=True)
def generate_test(story: str, output_dir: str) -> None:
    """Generate a complete pytest test class from a user story file."""
    parser = StoryParser()
    gen = CodeGenerator()

    user_story = parser.parse_story_file(story)
    story_id = re.sub(r"\W+", "_", user_story.get("id", "generated").lower()).strip("_")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    test_file = output_path / f"test_{story_id}.py"
    source = gen.generate_test_class(user_story)

    # Validate the generated code compiles before writing
    try:
        compile(source, str(test_file), "exec")
    except SyntaxError as exc:
        click.echo(click.style(f"  [ERROR] Generated code has a syntax error: {exc}", fg="red"), err=True)
        raise SystemExit(1) from exc

    test_file.write_text(source, encoding="utf-8")

    click.echo(click.style(f"  [OK] {test_file}", fg="green"))
    click.echo(f"       Story : {user_story.get('title', 'Untitled')}")
    click.echo(f"       Steps : {len(user_story.get('steps', []))}")
    neg = user_story.get("negative_scenarios", [])
    if neg:
        click.echo(f"       Negative scenarios: {len(neg)}")


# ── run ───────────────────────────────────────────────────────────────────────

@framework.command("run")
@click.option("--suite", default="tests/", show_default=True, help="Path to test file or directory")
@click.option("--browser-type", default="chromium", show_default=True,
              type=click.Choice(["chromium", "firefox", "webkit"]))
@click.option("--headless", is_flag=True, default=False)
@click.option("--no-report", is_flag=True, default=False, help="Skip HTML report generation")
@click.option("-k", "keyword", default=None, help="Pytest keyword expression filter")
@click.option("--base-url", default=None, help="Override the application base URL for this run")
def run(
    suite: str,
    browser_type: str,
    headless: bool,
    no_report: bool,
    keyword: Optional[str],
    base_url: Optional[str],
) -> None:
    """Execute the test suite with optional HTML reporting."""
    env = os.environ.copy()
    env["BROWSER"] = browser_type
    env["HEADLESS"] = "true" if headless else "false"
    if base_url:
        env["BASE_URL"] = base_url

    cmd = [sys.executable, "-m", "pytest", suite, "-v", "--tb=short"]

    if keyword:
        cmd += ["-k", keyword]
    if not no_report:
        Path("reports").mkdir(exist_ok=True)
        cmd += ["--html=reports/report.html", "--self-contained-html"]

    click.echo(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env)
    sys.exit(result.returncode)


# ── memory ────────────────────────────────────────────────────────────────────

@framework.command("memory")
@click.option("--action", type=click.Choice(["show", "search", "clear"]), default="show")
@click.option("--query", default="", help="Search query (used with --action search)")
def memory_cmd(action: str, query: str) -> None:
    """Inspect or manage the local memory engine."""
    mem = MemoryEngine()

    if action == "show":
        click.echo(mem.dump_summary())
        for entry in mem.get_all_context()["entries"]:
            click.echo(f"\n  [{entry['category']}] {entry['key']}")
            click.echo(f"    {entry['value']}")
            if entry.get("tags"):
                click.echo(f"    tags: {', '.join(entry['tags'])}")

    elif action == "search":
        if not query:
            raise click.UsageError("--query is required with --action search")
        results = mem.search(query)
        click.echo(f"Found {len(results)} result(s) for '{query}':")
        for r in results:
            click.echo(f"  [{r['category']}] {r['key']} → {r['value']}")

    elif action == "clear":
        if click.confirm("Delete all memory entries? This cannot be undone."):
            import shutil
            shutil.rmtree("memory", ignore_errors=True)
            click.echo(click.style("Memory cleared.", fg="yellow"))


# ── Private helpers ───────────────────────────────────────────────────────────

def _url_to_class_name(url: str) -> str:
    path = urlparse(url).path.strip("/").split("/")
    segment = path[-1] if path and path[-1] else urlparse(url).netloc.split(".")[0]
    return "".join(w.capitalize() for w in re.split(r"[\W_-]+", segment) if w) or "Page"


def _camel_to_snake(name: str) -> str:
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).lower()


if __name__ == "__main__":
    framework()
