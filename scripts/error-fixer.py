#!/usr/bin/env python3
"""Error diagnosis and auto-fix CLI for OpenClaw."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from scripts.lib.error_database import ErrorDatabase
from scripts.lib.error_parser import ErrorParser
from scripts.lib.fix_engine import FixEngine

console = Console()


def severity_badge(severity: str) -> str:
    """Return colored severity badge."""
    colors = {
        "critical": "[red bold]●[/red bold] CRITICAL",
        "high": "[red]●[/red] HIGH",
        "medium": "[yellow]●[/yellow] MEDIUM",
        "low": "[blue]●[/blue] LOW"
    }
    return colors.get(severity, severity.upper())


@click.command()
@click.option("--input", "input_file", type=click.Path(exists=True), help="Log file to analyze")
@click.option("--error", "error_code", help="Direct error code lookup")
@click.option("--auto-fix", is_flag=True, help="Execute safe auto-fixes")
@click.option("--dry-run", is_flag=True, help="Show what would be fixed without executing")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.option("--category", help="Filter by error category")
def main(input_file, error_code, auto_fix, dry_run, json_output, category):
    """OpenClaw Error Diagnosis and Auto-Fix Tool."""
    db = ErrorDatabase()
    parser = ErrorParser()
    fix_engine = FixEngine()

    # Category listing mode
    if category:
        patterns = db.get_by_category(category)
        if json_output:
            data = [{"code": p.code, "title": p.title, "severity": p.severity} for p in patterns]
            console.print_json(data=data)
        else:
            console.print(f"\n[bold]Errors in category: {category}[/bold]\n")
            for p in patterns:
                console.print(f"{severity_badge(p.severity)} {p.code}: {p.title}")
        return

    # Parse errors
    errors = []
    if error_code:
        # Direct code lookup
        patterns = db.match_exact_code(error_code)
        if not patterns:
            console.print(f"[red]Error code not found: {error_code}[/red]")
            sys.exit(1)
        errors = [(error_code, error_code, patterns)]
    elif input_file:
        # Parse log file
        parsed = parser.parse_log_file(Path(input_file))
        for pe in parsed:
            patterns = db.diagnose(pe.error_message, pe.error_code)
            if patterns:
                errors.append((pe.error_message, pe.error_code, patterns))
    else:
        # Read from stdin
        parsed = parser.parse_stdin()
        for pe in parsed:
            patterns = db.diagnose(pe.error_message, pe.error_code)
            if patterns:
                errors.append((pe.error_message, pe.error_code, patterns))

    if not errors:
        console.print("[yellow]No errors detected.[/yellow]")
        return

    # Output results
    if json_output:
        output_data = []
        for msg, code, patterns in errors:
            for p in patterns:
                output_data.append({
                    "code": p.code,
                    "severity": p.severity,
                    "title": p.title,
                    "description": p.description,
                    "causes": p.causes,
                    "fix_steps": p.fix_steps,
                    "auto_fixable": bool(p.fix_recipe_id and fix_engine.can_auto_fix(p.fix_recipe_id))
                })
        console.print_json(data=output_data)
        return

    # Rich panel output
    auto_fixable = 0
    manual_needed = 0

    for msg, code, patterns in errors:
        for p in patterns:
            # Build panel content
            content = []
            content.append(f"[bold]{severity_badge(p.severity)}[/bold]")
            content.append(f"\n{p.description}\n")

            if p.causes:
                content.append("[bold cyan]Possible Causes:[/bold cyan]")
                for cause in p.causes:
                    content.append(f"  • {cause}")
                content.append("")

            if p.fix_steps:
                content.append("[bold green]Fix Steps:[/bold green]")
                for i, step in enumerate(p.fix_steps, 1):
                    content.append(f"  {i}. {step}")
                content.append("")

            if p.fix_recipe_id and fix_engine.can_auto_fix(p.fix_recipe_id):
                content.append("[bold yellow]⚡ Auto-fix available[/bold yellow]")
                auto_fixable += 1
            else:
                manual_needed += 1

            if p.doc_url:
                content.append(f"\n[dim]Documentation: {p.doc_url}[/dim]")

            panel = Panel(
                "\n".join(content),
                title=f"[bold]{p.code}: {p.title}[/bold]",
                border_style="red" if p.severity in ["critical", "high"] else "yellow"
            )
            console.print(panel)

    # Summary
    console.print(f"\n[bold]Summary:[/bold] {len(errors)} errors found, {auto_fixable} auto-fixable, {manual_needed} need manual intervention\n")

    # Auto-fix execution
    if auto_fix and auto_fixable > 0:
        console.print("[bold yellow]Executing auto-fixes...[/bold yellow]\n")
        for msg, code, patterns in errors:
            for p in patterns:
                if p.fix_recipe_id and fix_engine.can_auto_fix(p.fix_recipe_id):
                    result = fix_engine.execute(p.fix_recipe_id, dry_run=dry_run)
                    if result.success:
                        console.print(f"[green]✓[/green] {result.message}")
                    else:
                        console.print(f"[red]✗[/red] {result.message}")
                    for action in result.actions_taken:
                        console.print(f"  {action}")


if __name__ == "__main__":
    main()
