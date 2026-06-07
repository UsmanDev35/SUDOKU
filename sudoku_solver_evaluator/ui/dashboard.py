from __future__ import annotations
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from sudoku_solver_evaluator.models.enums import DifficultyLevel, SolverType
from sudoku_solver_evaluator.models.metrics import AggregateStats, AlgorithmStats, ComparisonTable, SolveResult
_SOLVER_NAMES: dict[SolverType, str] = {SolverType.BACKTRACKING: 'Backtracking', SolverType.INFORMED: 'Informed (AC-3+MRV)', SolverType.LOCAL_SEARCH: 'Simulated Annealing', SolverType.FORWARD_CHECKING: 'Forward Checking'}
_BAR_CHAR = '█'
_BAR_HALF = '▌'
_BAR_MAX_WIDTH = 40

def render_comparison_table(comparison: ComparisonTable, console: Optional[Console]=None) -> None:
    # Render a comparison table showing solver performance for a single puzzle.
    if console is None:
        console = Console()
    table = Table(title=f'Performance Comparison — Puzzle: {comparison.puzzle_id}', caption=f'Difficulty: {comparison.difficulty.value.capitalize()}', show_header=True, header_style='bold cyan')
    table.add_column('Algorithm', style='bold', min_width=22)
    table.add_column('Time (ms)', justify='right', min_width=10)
    table.add_column('States Explored', justify='right', min_width=15)
    table.add_column('Backtracks', justify='right', min_width=10)
    table.add_column('Optimality Rank', justify='center', min_width=15)
    results = comparison.results
    if not results:
        console.print('[yellow]No results to display.[/yellow]')
        return
    best_time = min((r.time_ms for r in results.values()))
    best_states = min((r.states_explored for r in results.values()))
    best_backtracks = min((r.backtracks for r in results.values()))
    rankings = comparison.rankings.get('states_explored', [])
    for solver_type, result in results.items():
        name = _SOLVER_NAMES.get(solver_type, solver_type.value)
        time_text = _format_metric(result.time_ms, best_time)
        states_text = _format_metric(result.states_explored, best_states)
        backtracks_text = _format_metric(result.backtracks, best_backtracks)
        rank = rankings.index(solver_type) + 1 if solver_type in rankings else '-'
        rank_text = Text(str(rank))
        if rank == 1:
            rank_text.stylize('bold green')
        table.add_row(name, time_text, states_text, backtracks_text, rank_text)
    console.print()
    console.print(table)
    console.print()

def render_aggregate_table(aggregate: AggregateStats, console: Optional[Console]=None) -> None:
    # Render aggregate statistics table for a difficulty level.
    if console is None:
        console = Console()
    difficulty_name = aggregate.difficulty.value.capitalize()
    table = Table(title=f'Aggregate Statistics — {difficulty_name} ({aggregate.puzzle_count} puzzles)', show_header=True, header_style='bold cyan')
    table.add_column('Algorithm', style='bold', min_width=22)
    table.add_column('Time (ms)\nmean/min/max', justify='right', min_width=16)
    table.add_column('States\nmean/min/max', justify='right', min_width=16)
    table.add_column('Backtracks\nmean/min/max', justify='right', min_width=16)
    table.add_column('Solve Rate', justify='center', min_width=10)
    if not aggregate.stats:
        console.print('[yellow]No aggregate statistics to display.[/yellow]')
        return
    best_mean_time = min((s.mean_time_ms for s in aggregate.stats.values()))
    best_mean_states = min((s.mean_states for s in aggregate.stats.values()))
    best_mean_backtracks = min((s.mean_backtracks for s in aggregate.stats.values()))
    for solver_type, stats in aggregate.stats.items():
        name = _SOLVER_NAMES.get(solver_type, solver_type.value)
        time_str = f'{stats.mean_time_ms:.1f} / {stats.min_time_ms} / {stats.max_time_ms}'
        time_text = Text(time_str)
        if stats.mean_time_ms == best_mean_time:
            time_text.stylize('bold green')
        states_str = f'{stats.mean_states:.1f} / {stats.min_states} / {stats.max_states}'
        states_text = Text(states_str)
        if stats.mean_states == best_mean_states:
            states_text.stylize('bold green')
        bt_str = f'{stats.mean_backtracks:.1f} / {stats.min_backtracks} / {stats.max_backtracks}'
        bt_text = Text(bt_str)
        if stats.mean_backtracks == best_mean_backtracks:
            bt_text.stylize('bold green')
        rate_str = f'{stats.solve_rate * 100:.0f}%'
        rate_text = Text(rate_str)
        if stats.solve_rate == 1.0:
            rate_text.stylize('bold green')
        elif stats.solve_rate < 0.5:
            rate_text.stylize('red')
        table.add_row(name, time_text, states_text, bt_text, rate_text)
    console.print()
    console.print(table)
    console.print()

def render_performance_chart(results: dict[SolverType, SolveResult], metric: str='states_explored', console: Optional[Console]=None) -> None:
    # Render a simple horizontal bar chart for the given performance metric.
    if console is None:
        console = Console()
    if not results:
        console.print('[yellow]No results to chart.[/yellow]')
        return
    metric_values: dict[SolverType, int] = {}
    for solver_type, result in results.items():
        value = getattr(result, metric, 0)
        metric_values[solver_type] = value
    max_value = max(metric_values.values()) if metric_values else 1
    if max_value == 0:
        max_value = 1
    best_value = min(metric_values.values())
    metric_label = metric.replace('_', ' ').title()
    chart_lines: list[Text] = []
    for solver_type, value in sorted(metric_values.items(), key=lambda x: x[1]):
        name = _SOLVER_NAMES.get(solver_type, solver_type.value)
        bar_width = int(value / max_value * _BAR_MAX_WIDTH)
        if value > 0 and bar_width == 0:
            bar_width = 1
        bar = _BAR_CHAR * bar_width
        line = Text()
        padded_name = f'{name:<24}'
        line.append(padded_name, style='bold')
        if value == best_value:
            line.append(bar, style='bold green')
        else:
            line.append(bar, style='blue')
        line.append(f' {value:,}', style='dim')
        chart_lines.append(line)
    chart_content = Text('\n').join(chart_lines)
    panel = Panel(chart_content, title=f'[bold]{metric_label} Comparison[/bold]', border_style='cyan')
    console.print()
    console.print(panel)
    console.print()

def render_grouped_by_difficulty(comparisons: dict[DifficultyLevel, list[ComparisonTable]], console: Optional[Console]=None) -> None:
    # Render comparison tables grouped by puzzle difficulty.
    if console is None:
        console = Console()
    for difficulty in DifficultyLevel:
        tables = comparisons.get(difficulty, [])
        if not tables:
            continue
        console.print()
        console.rule(f'[bold magenta]{difficulty.value.capitalize()} Difficulty[/bold magenta]')
        for comparison in tables:
            render_comparison_table(comparison, console=console)

def render_full_dashboard(comparisons: list[ComparisonTable], aggregates: dict[DifficultyLevel, AggregateStats], console: Optional[Console]=None) -> None:
    # Render the full dashboard including grouped comparisons and aggregate stats.
    if console is None:
        console = Console()
    console.print()
    console.rule('[bold cyan]Comparative Analysis Dashboard[/bold cyan]')
    console.print()
    grouped: dict[DifficultyLevel, list[ComparisonTable]] = {}
    for comp in comparisons:
        grouped.setdefault(comp.difficulty, []).append(comp)
    render_grouped_by_difficulty(grouped, console=console)
    console.print()
    console.rule('[bold cyan]Aggregate Statistics[/bold cyan]')
    for difficulty in DifficultyLevel:
        if difficulty in aggregates:
            render_aggregate_table(aggregates[difficulty], console=console)
    if comparisons:
        last_comparison = comparisons[-1]
        if last_comparison.results:
            console.rule('[bold cyan]Performance Chart (Latest Puzzle)[/bold cyan]')
            render_performance_chart(last_comparison.results, metric='states_explored', console=console)
            render_performance_chart(last_comparison.results, metric='time_ms', console=console)

def _format_metric(value: int, best_value: int) -> Text:
    # Format a numeric metric and style it if it is the best value.
    text = Text(f'{value:,}')
    if value == best_value:
        text.stylize('bold green')
    return text