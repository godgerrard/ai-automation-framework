"""
Framework CLI — developer-facing code-generation and test-execution commands.

Install entry point (after pip install -e .):
    framework <command>

Direct invocation (without install):
    python -m cli.commands <command>
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import click

from core.memory_engine import MemoryEngine
from utils.helpers import (
    APICodeGenerator,
    AllureTestGenerator,
    AutoDOMMapper,
    CodeGenerator,
    NaturalLanguageStoryParser,
    ProjectScaffolder,
    StoryParser,
)


@click.group()
@click.version_option("2.1.0", prog_name="framework")
def framework() -> None:
    """AI-Augmented Test Automation Framework CLI.

    \b
    Workflow:
      1. framework setup          — interactive wizard (URL, credentials, browser)
      2. framework add-story      — convert plain English to story JSON
      3. framework build          — probe DOM + generate test code (no TODOs)
      4. framework run            — run tests + publish Allure dashboard

    \b
    Repair:
      framework fix-selector      — patch a broken locator in-place
    """


# ── setup ─────────────────────────────────────────────────────────────────────

@framework.command("setup")
@click.option("--non-interactive", is_flag=True, default=False,
              help="Skip prompts (use --url / --name flags instead)")
@click.option("--url", default=None, help="Application base URL")
@click.option("--name", default=None, help="Short project name (e.g. myapp)")
@click.option("--browser", default=None,
              type=click.Choice(["chromium", "firefox", "webkit"]),
              help="Default browser for Playwright tests")
@click.option("--username", default=None, help="App username (saved to .env, never committed)")
@click.option("--password", default=None, help="App password (saved to .env, never committed)")
def setup(non_interactive: bool, url: Optional[str], name: Optional[str],
          browser: Optional[str], username: Optional[str], password: Optional[str]) -> None:
    """Interactive wizard: configure a new project and write .env + config.json.

    Run this first when onboarding a new application under test.

    \b
    What it does
    ------------
    - Asks for app URL, project name, credentials, and browser preference
    - Writes .env with credentials (gitignored — never committed)
    - Updates config.json with base_url and browser settings
    - Scaffolds locators/, pages/, tests/, stories/ skeletons
    """
    click.echo()
    click.echo(click.style("  AI Automation Framework - Project Setup", bold=True))
    click.echo(click.style("  -----------------------------------------", fg="blue"))
    click.echo()

    # Collect inputs
    if non_interactive:
        if not url or not name:
            raise click.UsageError("--url and --name are required with --non-interactive")
        app_url = url
        project_name = name
        browser_choice = browser or "chromium"
        username = username or ""
        password = password or ""
    else:
        app_url = url or click.prompt(
            "  Application URL",
            default="https://yourapp.com",
        )
        project_name = name or click.prompt(
            "  Project name (no spaces, e.g. myapp)",
            default=_url_to_project_name(app_url),
        )
        browser_choice = browser or click.prompt(
            "  Default browser",
            type=click.Choice(["chromium", "firefox", "webkit"]),
            default="chromium",
        )
        has_auth = click.confirm("  Does the app require login credentials?", default=True)
        if has_auth:
            username = click.prompt(f"  {project_name.upper()}_USERNAME", default="")
            password = click.prompt(f"  {project_name.upper()}_PASSWORD", hide_input=True, default="")
        else:
            username = ""
            password = ""

    click.echo()
    click.echo(click.style("  Writing configuration…", fg="cyan"))

    # Write .env
    env_lines: list[str] = []
    env_path = Path(".env")
    if env_path.exists():
        env_lines = [l for l in env_path.read_text(encoding="utf-8").splitlines()
                     if l and not l.startswith(f"{project_name.upper()}_")
                     and not l.startswith("BASE_URL=") and not l.startswith("BROWSER=")]
    env_lines += [
        f"BASE_URL={app_url}",
        f"BROWSER={browser_choice}",
    ]
    if username:
        env_lines.append(f"{project_name.upper()}_USERNAME={username}")
    if password:
        env_lines.append(f"{project_name.upper()}_PASSWORD={password}")
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    click.echo(click.style("  [written] .env", fg="green"))

    # Update config.json
    config_path = Path("config.json")
    config: dict = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            config = {}
    config.setdefault("app", {})
    config["app"]["base_url"] = app_url
    config.setdefault("browser", {})
    config["browser"]["browser"] = browser_choice
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    click.echo(click.style("  [written] config.json", fg="green"))

    # Scaffold project files
    click.echo(click.style("  Scaffolding project skeleton…", fg="cyan"))
    scaffolder = ProjectScaffolder(app_url, project_name, "both")
    created = scaffolder.scaffold()
    for path in created:
        click.echo(click.style(f"  [created] {path}", fg="green"))

    click.echo()
    click.echo(click.style("  Setup complete!", fg="green", bold=True))
    click.echo()
    click.echo(click.style("  Next steps:", bold=True))
    click.echo(f"    framework add-story --text 'As a {project_name} user I want to log in'")
    click.echo(f"    framework build")
    click.echo(f"    framework run")
    click.echo()


# ── add-story ─────────────────────────────────────────────────────────────────

@framework.command("add-story")
@click.option("--text", default=None, help="Plain English story text (inline)")
@click.option("--file", "story_file", default=None, type=click.Path(exists=True),
              help="Path to a .txt file containing the story")
@click.option("--output-dir", default="stories", show_default=True,
              help="Directory to write story JSON files")
def add_story(text: Optional[str], story_file: Optional[str], output_dir: str) -> None:
    """Convert plain English requirements into structured story JSON.

    Accepts inline text (--text) or a .txt file (--file).
    Multiple stories can be separated with '---' in the input.

    \b
    Examples
    --------
    framework add-story --text "As a user I want to log in and see the dashboard"

    framework add-story --file requirements.txt

    \b
    After adding stories, run:
        framework build         (probes DOM + generates test code)
    """
    if not text and not story_file:
        raise click.UsageError("Provide --text or --file")

    if story_file:
        raw = Path(story_file).read_text(encoding="utf-8")
    else:
        raw = text or ""

    parser = NaturalLanguageStoryParser()
    stories = parser.parse(raw)

    if not stories:
        click.echo(click.style("  [ERROR] No stories parsed from input.", fg="red"), err=True)
        raise SystemExit(1)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    click.echo()
    for story in stories:
        story_id = story.get("id", "story_001")
        out_file = output_path / f"{story_id}.json"
        out_file.write_text(json.dumps(story, indent=2), encoding="utf-8")
        click.echo(click.style(f"  [created] {out_file}", fg="green"))
        click.echo(f"           Title : {story.get('title', 'Untitled')}")
        click.echo(f"           Steps : {len(story.get('steps', []))}")
        neg = story.get("negative_scenarios", [])
        if neg:
            click.echo(f"           Negative scenarios: {len(neg)}")

    click.echo()
    click.echo(click.style("  Next step:", bold=True) + "  framework build")
    click.echo()


# ── build ─────────────────────────────────────────────────────────────────────

@framework.command("build")
@click.option("--story", "story_path", default=None, type=click.Path(exists=True),
              help="Build a single story file (default: all stories/*.json)")
@click.option("--base-url", default=None,
              help="Override base URL (default: from config.json / .env)")
@click.option("--no-probe", is_flag=True, default=False,
              help="Skip live DOM probing (keeps TODO selectors — useful offline)")
@click.option("--username", default=None, help="App username (overrides .env)")
@click.option("--password", default=None, help="App password (overrides .env)")
def build(
    story_path: Optional[str],
    base_url: Optional[str],
    no_probe: bool,
    username: Optional[str],
    password: Optional[str],
) -> None:
    """Probe the live DOM and generate complete test code from story files.

    This is the core command of the four-loop pipeline.
    It reads story JSON, probes the live app for real selectors,
    then writes locators, page objects, and pytest test files.

    \b
    What it generates (per story)
    -----------------------------
    locators/<project>_locators.py   — real CSS/data-test selectors
    pages/<project>_page.py          — page object with action methods
    tests/workflows/test_<id>.py     — pytest class with Allure markers

    \b
    No TODOs in output (unless --no-probe is used and a selector can't be found).
    """
    # Resolve base URL
    resolved_url = base_url or os.getenv("BASE_URL") or _read_config_url()
    if not resolved_url:
        click.echo(
            click.style("  [ERROR] ", fg="red") +
            "No base URL found. Run 'framework setup' first or pass --base-url.",
            err=True,
        )
        raise SystemExit(1)

    # Collect story files
    if story_path:
        story_files = [Path(story_path)]
    else:
        story_files = sorted(Path("stories").glob("*.json"))
        # Skip template files
        story_files = [f for f in story_files if "template" not in f.name.lower()]

    if not story_files:
        click.echo(
            click.style("  [ERROR] ", fg="red") +
            "No story files found in stories/. Run 'framework add-story' first.",
            err=True,
        )
        raise SystemExit(1)

    # Resolve credentials for auto-login
    creds: dict | None = None
    u = username or os.getenv("USERNAME") or _first_env_credential("USERNAME")
    p = password or os.getenv("PASSWORD") or _first_env_credential("PASSWORD")
    if u and p:
        creds = {"username": u, "password": p}

    mapper = AutoDOMMapper(resolved_url, creds) if not no_probe else None
    gen = AllureTestGenerator()

    click.echo()
    click.echo(click.style(f"  Building from {len(story_files)} story file(s)…", bold=True))
    click.echo(f"  Target URL : {resolved_url}")
    click.echo(f"  DOM probe  : {'enabled' if not no_probe else 'disabled (--no-probe)'}")
    click.echo()

    all_created: list[str] = []
    has_todos = False

    for story_file in story_files:
        raw_story = json.loads(story_file.read_text(encoding="utf-8"))
        raw_story.setdefault("base_url", resolved_url)

        click.echo(click.style(f"  Processing {story_file.name}…", fg="cyan"))

        # Enrich story with real selectors
        if mapper:
            try:
                story = mapper.enrich_story(raw_story)
                click.echo("    DOM probe  : OK")
            except Exception as exc:
                click.echo(click.style(f"    DOM probe  : FAILED ({exc})", fg="yellow"))
                story = raw_story
        else:
            story = raw_story

        story_id = story.get("id", story_file.stem)
        project_name = _story_to_project_name(story_id)

        # Check for remaining TODOs
        todo_count = sum(
            1 for s in story.get("steps", [])
            if "TODO" in (s.get("target") or "")
        )
        if todo_count:
            has_todos = True
            click.echo(click.style(f"    Selectors  : {todo_count} TODO(s) remain — run 'framework fix-selector' or probe manually", fg="yellow"))
        else:
            click.echo(click.style(f"    Selectors  : all resolved", fg="green"))

        # Generate locators file
        created = _write_locators(story, project_name)
        for path in created:
            click.echo(click.style(f"    [created] {path}", fg="green"))
            all_created.append(path)

        # Generate page object
        page_path = _write_page_object(story, project_name, resolved_url)
        click.echo(click.style(f"    [created] {page_path}", fg="green"))
        all_created.append(page_path)

        # Generate test file with Allure
        test_source = gen.generate(story, project_name)
        test_dir = Path("tests/workflows")
        test_dir.mkdir(parents=True, exist_ok=True)
        _ensure_init(test_dir)

        test_file = test_dir / f"test_{story_id}.py"
        try:
            compile(test_source, str(test_file), "exec")
        except SyntaxError as exc:
            click.echo(click.style(f"    [ERROR] Syntax error in generated test: {exc}", fg="red"), err=True)
            continue

        test_file.write_text(test_source, encoding="utf-8")
        click.echo(click.style(f"    [created] {test_file}", fg="green"))
        all_created.append(str(test_file))

        # Write back the enriched story (with resolved selectors)
        story_file.write_text(json.dumps(story, indent=2), encoding="utf-8")

        click.echo()

    click.echo(click.style(f"  Build complete — {len(all_created)} file(s) generated.", bold=True))
    if has_todos:
        click.echo(click.style("  Some selectors need manual fixing:", fg="yellow"))
        click.echo("    framework fix-selector --file locators/<name>_locators.py --constant <NAME> --selector '<selector>'")
    click.echo()
    click.echo(click.style("  Next step:", bold=True) + "  framework run")
    click.echo()


# ── fix-selector ──────────────────────────────────────────────────────────────

@framework.command("fix-selector")
@click.option("--file", "locator_file", required=True, type=click.Path(exists=True),
              help="Path to the locators file (e.g. locators/myapp_locators.py)")
@click.option("--constant", required=True, help="Name of the constant to patch (e.g. LOGIN_BUTTON)")
@click.option("--selector", required=True, help="New selector value (e.g. [data-test='login-button'])")
def fix_selector(locator_file: str, constant: str, selector: str) -> None:
    """Patch a single locator constant in a locator file.

    Used by the CORRECTOR LOOP when a test fails due to a selector mismatch.
    The MCP inspect_current_dom tool finds the real selector; this command
    writes it into the locator file without touching any other constants.

    \b
    Examples
    --------
    framework fix-selector \\
        --file locators/myapp_locators.py \\
        --constant LOGIN_BUTTON \\
        --selector "[data-test='login-button']"
    """
    path = Path(locator_file)
    source = path.read_text(encoding="utf-8")

    # Match:  CONSTANT_NAME = "old-value"  (single or double quotes)
    pattern = re.compile(
        rf'^(\s*{re.escape(constant)}\s*=\s*)["\']([^"\']*)["\']',
        re.MULTILINE,
    )
    match = pattern.search(source)
    if not match:
        click.echo(
            click.style(f"  [ERROR] ", fg="red") +
            f"Constant '{constant}' not found in {locator_file}.\n"
            f"  Available constants:",
            err=True,
        )
        for line in source.splitlines():
            m = re.match(r'\s*([A-Z_][A-Z0-9_]+)\s*=', line)
            if m:
                click.echo(f"    {m.group(1)}", err=True)
        raise SystemExit(1)

    old_selector = match.group(2)
    new_source = pattern.sub(rf'\g<1>"{selector}"', source)
    path.write_text(new_source, encoding="utf-8")

    click.echo()
    click.echo(click.style(f"  [fixed] {locator_file}", fg="green"))
    click.echo(f"  Constant : {constant}")
    click.echo(click.style(f"  Before   : {old_selector}", fg="red"))
    click.echo(click.style(f"  After    : {selector}", fg="green"))

    # Record to memory engine so Corrector can track the fix
    mem = MemoryEngine()
    mem.record_selector_fix(
        page_name=path.stem,
        element_name=constant,
        original=old_selector,
        fixed=selector,
        reason="corrector-loop fix via CLI",
    )
    click.echo()


# ── run ───────────────────────────────────────────────────────────────────────

@framework.command("run")
@click.option("--suite", default="tests/", show_default=True,
              help="Path to test file or directory")
@click.option("--browser-type", default="chromium", show_default=True,
              type=click.Choice(["chromium", "firefox", "webkit"]))
@click.option("--headless", is_flag=True, default=False)
@click.option("--no-report", is_flag=True, default=False, help="Skip HTML report generation")
@click.option("--alluredir", default="allure-results", show_default=True,
              help="Directory to write Allure result files")
@click.option("--no-allure", is_flag=True, default=False,
              help="Skip Allure result collection")
@click.option("-k", "keyword", default=None, help="Pytest keyword expression filter")
@click.option("--base-url", default=None, help="Override the application base URL for this run")
@click.option("--marker", "-m", default=None, help="Run only tests matching this marker (e.g. smoke)")
def run(
    suite: str,
    browser_type: str,
    headless: bool,
    no_report: bool,
    alluredir: str,
    no_allure: bool,
    keyword: Optional[str],
    base_url: Optional[str],
    marker: Optional[str],
) -> None:
    """Execute the test suite with pytest + Allure reporting.

    \b
    Examples
    --------
    # Full suite with Allure
    framework run

    # Specific browser, headed mode
    framework run --browser-type firefox --headless

    # Only smoke tests
    framework run --marker smoke

    # Keyword filter
    framework run -k "login"
    """
    env = os.environ.copy()
    env["BROWSER"] = browser_type
    env["HEADLESS"] = "true" if headless else "false"
    if base_url:
        env["BASE_URL"] = base_url

    cmd = [sys.executable, "-m", "pytest", suite, "-v", "--tb=short"]

    if keyword:
        cmd += ["-k", keyword]
    if marker:
        cmd += ["-m", marker]
    if not no_report:
        Path("reports").mkdir(exist_ok=True)
        cmd += ["--html=reports/report.html", "--self-contained-html"]
    if not no_allure:
        Path(alluredir).mkdir(exist_ok=True)
        cmd += [f"--alluredir={alluredir}"]

    click.echo(f"\nRunning: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, env=env)

    # Generate Allure HTML report if results exist
    if not no_allure and Path(alluredir).exists():
        _generate_allure_report(alluredir)

    sys.exit(result.returncode)


# ── init-project ──────────────────────────────────────────────────────────────

@framework.command("init-project")
@click.option("--url", required=True, help="Target application base URL (e.g. https://myapp.com)")
@click.option("--name", required=True, help="Short project name used as file prefix (e.g. myapp)")
@click.option(
    "--type", "project_type",
    type=click.Choice(["web", "api", "both"]),
    default="both",
    show_default=True,
    help="Scaffold web (Playwright), api (HTTP), or both.",
)
def init_project(url: str, name: str, project_type: str) -> None:
    """Scaffold a test project skeleton for a new application.

    Creates ready-to-edit locators, page objects, story files, and test stubs.
    All generated files are listed in .gitignore — they never pollute the framework repo.

    \b
    Prefer 'framework setup' for first-time onboarding (interactive wizard).
    Use this command for scripted or CI-driven scaffolding.
    """
    scaffolder = ProjectScaffolder(url, name, project_type)
    created = scaffolder.scaffold()

    if not created:
        click.echo(click.style("  [skipped] All files already exist — nothing to create.", fg="yellow"))
        return

    click.echo()
    for path in created:
        click.echo(click.style(f"  [created] {path}", fg="green"))

    click.echo()
    click.echo(click.style("Next steps:", bold=True))
    click.echo(f"  1. Add a story:        framework add-story --text 'As a user I want to ...'")
    click.echo(f"  2. Build test code:    framework build --base-url {url}")
    click.echo(f"  3. Run:                framework run")
    click.echo()
    click.echo(
        click.style("Note: ", fg="yellow", bold=True)
        + "Generated files are .gitignored. Commit them only in your own fork/branch."
    )


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
    """Generate a complete pytest test class from a user story file.

    Prefer 'framework build' which also probes the live DOM for real selectors.
    Use this command if you have a hand-crafted story JSON with selectors already filled in.
    """
    parser = StoryParser()
    gen = CodeGenerator()

    user_story = parser.parse_story_file(story)
    story_id = re.sub(r"\W+", "_", user_story.get("id", "generated").lower()).strip("_")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    test_file = output_path / f"test_{story_id}.py"
    source = gen.generate_test_class(user_story)

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


# ── generate-api-test ─────────────────────────────────────────────────────────

@framework.command("generate-api-test")
@click.option("--story", required=True, type=click.Path(exists=True), help="Path to API story JSON file")
@click.option("--output-dir", default="tests/api", show_default=True)
def generate_api_test(story: str, output_dir: str) -> None:
    """Generate a pytest API test class from an API story file."""
    parser = StoryParser()
    gen = APICodeGenerator()

    user_story = parser.parse_story_file(story)
    story_id = re.sub(r"\W+", "_", user_story.get("id", "generated").lower()).strip("_")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    init_file = output_path / "__init__.py"
    if not init_file.exists():
        init_file.write_text("", encoding="utf-8")

    test_file = output_path / f"test_{story_id}.py"
    source = gen.generate_test_class(user_story)

    try:
        compile(source, str(test_file), "exec")
    except SyntaxError as exc:
        click.echo(click.style(f"  [ERROR] Generated code has a syntax error: {exc}", fg="red"), err=True)
        raise SystemExit(1) from exc

    test_file.write_text(source, encoding="utf-8")

    click.echo(click.style(f"  [OK] {test_file}", fg="green"))
    click.echo(f"       Story    : {user_story.get('title', 'Untitled')}")
    click.echo(f"       Endpoints: {len(user_story.get('endpoints', []))}")
    neg = user_story.get("negative_scenarios", [])
    if neg:
        click.echo(f"       Negative : {len(neg)}")


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


def _url_to_project_name(url: str) -> str:
    netloc = urlparse(url).netloc
    # Strip www. and TLD
    parts = netloc.replace("www.", "").split(".")
    return parts[0].lower() if parts else "myapp"


def _camel_to_snake(name: str) -> str:
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).lower()


def _story_to_project_name(story_id: str) -> str:
    """Derive a short project name from a story ID (e.g. 'login_flow_001' → 'login')."""
    parts = story_id.split("_")
    # Drop trailing numeric segments
    while parts and parts[-1].isdigit():
        parts.pop()
    return "_".join(parts[:2]) if parts else "app"


def _read_config_url() -> str:
    config_path = Path("config.json")
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            return cfg.get("app", {}).get("base_url", "")
        except (json.JSONDecodeError, KeyError):
            return ""
    return ""


def _first_env_credential(suffix: str) -> str:
    """Find the first env var that ends with _USERNAME or _PASSWORD."""
    for key, val in os.environ.items():
        if key.endswith(f"_{suffix}") and val:
            return val
    return ""


def _write_locators(story: dict, project_name: str) -> list[str]:
    """Generate locators/<project>_locators.py from story steps."""
    steps = story.get("steps", [])
    seen: dict[str, str] = {}
    for step in steps:
        target = step.get("target", "")
        if not target or target == "/":
            continue
        desc = step.get("description", "")
        const_name = re.sub(r"[^A-Z0-9_]", "", re.sub(r"\W+", "_", desc.upper()))[:40].strip("_")
        if not const_name:
            const_name = f"ELEMENT_{len(seen)}"
        seen[const_name] = target

    lines = [
        '"""',
        f"Locators for: {story.get('title', 'Generated')}",
        f"Story ID : {story.get('id', 'unknown')}",
        "",
        "Auto-generated by framework build — edit selectors in-place.",
        "Use: framework fix-selector --file <this file> --constant <NAME> --selector <value>",
        '"""',
        "",
    ]
    for name, sel in seen.items():
        todo_marker = "  # TODO: find real selector" if "TODO" in sel else ""
        lines.append(f'{name} = "{sel}"{todo_marker}')

    source = "\n".join(lines) + "\n"
    locator_dir = Path("locators")
    locator_dir.mkdir(exist_ok=True)
    _ensure_init(locator_dir)

    out = locator_dir / f"{project_name}_locators.py"
    out.write_text(source, encoding="utf-8")
    return [str(out)]


def _write_page_object(story: dict, project_name: str, base_url: str) -> str:
    """Generate pages/<project>_page.py from story steps."""
    steps = story.get("steps", [])
    title = story.get("title", "Generated Page")
    class_name = "".join(w.capitalize() for w in re.split(r"[\W_]+", project_name) if w) + "Page"

    action_lines: list[str] = []
    current_method = "execute"
    method_steps: dict[str, list[str]] = {current_method: []}

    for step in steps:
        action = step.get("action", "")
        target = step.get("target", "")
        value = step.get("value", "")
        desc = step.get("description", "")

        if action == "navigate":
            current_method = "navigate_to_" + re.sub(r"\W+", "_", (target or "/").strip("/")) or "home"
            method_steps.setdefault(current_method, [])

        code = _step_to_page_method_line(action, target, value, desc)
        if code:
            method_steps.setdefault(current_method, []).append(code)

    lines = [
        '"""',
        f"Page Object for: {title}",
        '"""',
        "from __future__ import annotations",
        "",
        "from core.base_page import BasePage",
        "",
        "",
        f"class {class_name}(BasePage):",
        f'    """Page Object for {title}."""',
        "",
    ]

    for method_name, method_lines in method_steps.items():
        safe_name = re.sub(r"[^a-z0-9_]", "", method_name.lower())[:50] or "execute"
        lines.append(f"    def {safe_name}(self) -> None:")
        if method_lines:
            for ml in method_lines:
                lines.append(f"        {ml}")
        else:
            lines.append("        pass")
        lines.append("")

    source = "\n".join(lines)

    page_dir = Path("pages")
    page_dir.mkdir(exist_ok=True)
    _ensure_init(page_dir)

    out = page_dir / f"{project_name}_page.py"
    out.write_text(source, encoding="utf-8")
    return str(out)


def _step_to_page_method_line(action: str, target: str, value: str, desc: str) -> str:
    c = f"  # {desc}" if desc else ""
    if action == "fill":
        return f'self.fill("{target}", "{value}"){c}'
    if action == "click":
        return f'self.click("{target}"){c}'
    if action == "assert_visible":
        return f'assert self.is_visible("{target}"){c}'
    if action == "assert_text":
        return f'assert "{value}" in self.get_text("{target}"){c}'
    if action == "assert_url":
        return f'self.wait_for_url("**{target}"){c}'
    if action == "select":
        return f'self.select_option("{target}", "{value}"){c}'
    return ""


def _generate_allure_report(alluredir: str) -> None:
    """Try allure CLI first; fall back to pure-Python HTML summary."""
    import glob
    import json as _json
    from datetime import datetime

    # Try the allure CLI (requires Java)
    try:
        allure_cmd = ["allure", "generate", alluredir, "--clean", "-o", "allure-report"]
        gen = subprocess.run(allure_cmd, capture_output=True, text=True, timeout=60)
        if gen.returncode == 0:
            click.echo(click.style("  Dashboard  → allure-report/index.html", fg="green"))
            return
    except (FileNotFoundError, OSError):
        pass

    # Pure-Python fallback: parse result JSONs and write a summary HTML
    results = []
    for f in glob.glob(f"{alluredir}/*-result.json"):
        try:
            with open(f, encoding="utf-8") as fp:
                data = _json.load(fp)
            labels = {l["name"]: l["value"] for l in data.get("labels", [])}
            results.append({
                "name": data.get("name", "unknown"),
                "status": data.get("status", "unknown"),
                "feature": labels.get("feature", "General"),
                "story": labels.get("story", ""),
                "severity": labels.get("severity", "normal"),
                "duration_ms": data.get("stop", 0) - data.get("start", 0),
                "markers": [l["value"] for l in data.get("labels", []) if l["name"] == "tag"],
            })
        except Exception:
            continue

    if not results:
        click.echo(click.style("  [INFO] No allure results found.", fg="yellow"))
        return

    results.sort(key=lambda x: (x["feature"], x["name"]))
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    total = len(results)
    total_ms = sum(r["duration_ms"] for r in results)
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    features: dict = {}
    for r in results:
        features.setdefault(r["feature"], []).append(r)

    rows = ""
    for feat, tests in features.items():
        f_pass = sum(1 for t in tests if t["status"] == "passed")
        rows += (
            f'<tr class="feature-row"><td colspan="5"><b>{feat}</b>'
            f'&nbsp;<span class="badge badge-pass">{f_pass}/{len(tests)}</span></td></tr>'
        )
        for t in tests:
            cls = "pass" if t["status"] == "passed" else "fail"
            icon = "&#10003;" if t["status"] == "passed" else "&#10007;"
            badges = "".join(
                f'<span class="badge badge-tag">{m}</span>' for m in t["markers"]
            )
            rows += (
                f'<tr class="{cls}"><td><span class="icon-{cls}">{icon}</span></td>'
                f'<td>{t["name"]}{badges}</td><td>{t["story"]}</td>'
                f'<td>{t["severity"]}</td><td>{t["duration_ms"]}ms</td></tr>'
            )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><title>Test Report</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f4f6f9;color:#222}}
header{{background:#1a1a2e;color:#fff;padding:32px 40px}}
header h1{{font-size:1.8rem;font-weight:700}}
header p{{opacity:.7;margin-top:4px;font-size:.9rem}}
.summary{{display:flex;gap:20px;padding:28px 40px;flex-wrap:wrap}}
.card{{background:#fff;border-radius:10px;padding:22px 28px;box-shadow:0 1px 4px rgba(0,0,0,.08);min-width:140px}}
.card .num{{font-size:2.4rem;font-weight:800}}
.card .lbl{{font-size:.8rem;text-transform:uppercase;letter-spacing:.05em;opacity:.5;margin-top:2px}}
.num-pass{{color:#22c55e}}.num-fail{{color:#ef4444}}.num-total{{color:#6366f1}}.num-time{{color:#f59e0b}}
.progress-bar{{height:8px;background:#e5e7eb;border-radius:4px;margin:0 40px 8px}}
.progress-fill{{height:100%;border-radius:4px;background:#22c55e}}
.table-wrap{{margin:0 40px 40px;background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,.08);overflow:hidden}}
table{{width:100%;border-collapse:collapse}}
th{{background:#f8fafc;color:#64748b;font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;padding:12px 16px;text-align:left;border-bottom:1px solid #e2e8f0}}
td{{padding:11px 16px;font-size:.875rem;border-bottom:1px solid #f1f5f9;vertical-align:middle}}
tr.feature-row td{{background:#f8fafc;font-size:.8rem;padding:8px 16px;color:#6366f1;border-top:2px solid #e0e7ff}}
tr.pass:hover{{background:#f0fdf4}}tr.fail:hover{{background:#fef2f2}}
.icon-pass{{color:#22c55e;font-weight:700}}.icon-fail{{color:#ef4444;font-weight:700}}
.badge{{display:inline-block;font-size:.65rem;padding:1px 7px;border-radius:99px;margin-left:6px;font-weight:600;vertical-align:middle}}
.badge-pass{{background:#dcfce7;color:#15803d}}.badge-fail{{background:#fee2e2;color:#b91c1c}}.badge-tag{{background:#e0e7ff;color:#4338ca}}
.footer{{text-align:center;padding:20px;font-size:.75rem;color:#94a3b8}}
</style></head>
<body>
<header><h1>Test Report</h1><p>AI Automation Framework &bull; {run_date}</p></header>
<div class="summary">
  <div class="card"><div class="num num-total">{total}</div><div class="lbl">Total</div></div>
  <div class="card"><div class="num num-pass">{passed}</div><div class="lbl">Passed</div></div>
  <div class="card"><div class="num num-fail">{failed}</div><div class="lbl">Failed</div></div>
  <div class="card"><div class="num num-time">{total_ms/1000:.1f}s</div><div class="lbl">Duration</div></div>
</div>
<div class="progress-bar"><div class="progress-fill" style="width:{passed/total*100:.1f}%"></div></div>
<div class="table-wrap"><table>
<thead><tr><th style="width:40px"></th><th>Test</th><th>Story</th><th>Severity</th><th>Duration</th></tr></thead>
<tbody>{rows}</tbody>
</table></div>
<div class="footer">AI Automation Framework v2.0.0 &bull; Playwright + pytest + allure-pytest</div>
</body></html>"""

    Path("allure-report").mkdir(exist_ok=True)
    Path("allure-report/index.html").write_text(html, encoding="utf-8")
    click.echo(click.style("  Dashboard  -> allure-report/index.html", fg="green"))
    click.echo(
        click.style("  [INFO] ", fg="yellow") +
        "Install Java + allure CLI for full interactive Allure dashboard."
    )


def _ensure_init(directory: Path) -> None:
    init = directory / "__init__.py"
    if not init.exists():
        init.write_text("", encoding="utf-8")


if __name__ == "__main__":
    framework()
