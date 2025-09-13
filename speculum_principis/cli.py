"""
Command-line interface for Speculum Principis.

This module provides CLI commands for running and interacting with the agent.
"""

import asyncio
import click
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from .agent.core import SpeculumAgent
from .utils.config import Config


@click.group()
@click.option('--config', '-c', help='Path to configuration file')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def main(ctx, config: Optional[str], verbose: bool):
    """Speculum Principis - AI Agent for Monitoring Study Subjects."""
    # Load configuration
    ctx.ensure_object(dict)
    
    if config:
        ctx.obj['config'] = Config.from_env(config)
    else:
        ctx.obj['config'] = Config.from_env()
    
    # Override log level if verbose
    if verbose:
        ctx.obj['config'].log_level = "DEBUG"
    
    # Setup logging
    ctx.obj['config'].setup_logging()
    
    # Validate configuration
    if not ctx.obj['config'].validate():
        click.echo("Configuration validation failed. Check logs for details.", err=True)
        ctx.exit(1)


@main.command()
@click.pass_context
def start(ctx):
    """Start the monitoring agent."""
    config = ctx.obj['config']
    click.echo("Starting Speculum Principis agent...")
    click.echo(f"Configuration: {config}")
    
    async def run_agent():
        agent = SpeculumAgent(config)
        try:
            await agent.start()
        except KeyboardInterrupt:
            click.echo("\nShutting down agent...")
            await agent.stop()
        except Exception as e:
            click.echo(f"Error running agent: {e}", err=True)
            logging.error(f"Agent error: {e}")
    
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        click.echo("\nAgent stopped.")


@main.command()
@click.option('--days', '-d', default=7, help='Number of days to look back (default: 7)')
@click.option('--limit', '-l', default=20, help='Maximum number of subjects to show (default: 20)')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.pass_context
def subjects(ctx, days: int, limit: int, output_format: str):
    """List recently discovered subjects."""
    config = ctx.obj['config']
    
    async def list_subjects():
        agent = SpeculumAgent(config)
        await agent.db_manager.initialize()
        
        since_date = datetime.now() - timedelta(days=days)
        subjects_data = await agent.get_recent_subjects(days)
        
        if not subjects_data:
            click.echo(f"No subjects found in the last {days} days.")
            return
        
        # Limit results
        subjects_data = subjects_data[:limit]
        
        if output_format == 'json':
            click.echo(json.dumps(subjects_data, indent=2))
        else:
            click.echo(f"\nRecent subjects (last {days} days):")
            click.echo("-" * 80)
            click.echo(f"{'Subject':<30} {'Score':<8} {'Count':<8} {'Sources':<20}")
            click.echo("-" * 80)
            
            for subject in subjects_data:
                sources_str = ', '.join(subject['sources'][:3])
                if len(subject['sources']) > 3:
                    sources_str += f" (+{len(subject['sources']) - 3})"
                
                click.echo(
                    f"{subject['name'][:29]:<30} "
                    f"{subject['relevance_score']:<8.2f} "
                    f"{subject['occurrence_count']:<8} "
                    f"{sources_str:<20}"
                )
    
    try:
        asyncio.run(list_subjects())
    except Exception as e:
        click.echo(f"Error listing subjects: {e}", err=True)


@main.command()
@click.argument('query')
@click.option('--limit', '-l', default=10, help='Maximum number of results (default: 10)')
@click.option('--format', 'output_format', type=click.Choice(['table', 'json']), default='table', help='Output format')
@click.pass_context
def search(ctx, query: str, limit: int, output_format: str):
    """Search for subjects matching a query."""
    config = ctx.obj['config']
    
    async def search_subjects():
        agent = SpeculumAgent(config)
        await agent.db_manager.initialize()
        
        results = await agent.search_subjects(query)
        
        if not results:
            click.echo(f"No subjects found matching '{query}'.")
            return
        
        # Limit results
        results = results[:limit]
        
        if output_format == 'json':
            click.echo(json.dumps(results, indent=2))
        else:
            click.echo(f"\nSearch results for '{query}':")
            click.echo("-" * 80)
            click.echo(f"{'Subject':<30} {'Score':<8} {'Count':<8} {'First Seen':<12}")
            click.echo("-" * 80)
            
            for subject in results:
                first_seen = datetime.fromisoformat(subject['first_seen']).strftime('%Y-%m-%d')
                click.echo(
                    f"{subject['name'][:29]:<30} "
                    f"{subject['relevance_score']:<8.2f} "
                    f"{subject['occurrence_count']:<8} "
                    f"{first_seen:<12}"
                )
    
    try:
        asyncio.run(search_subjects())
    except Exception as e:
        click.echo(f"Error searching subjects: {e}", err=True)


@main.command()
@click.pass_context
def stats(ctx):
    """Show agent statistics."""
    config = ctx.obj['config']
    
    async def show_stats():
        agent = SpeculumAgent(config)
        await agent.db_manager.initialize()
        
        # Get database stats
        db_stats = await agent.db_manager.get_stats()
        
        # Get agent stats
        agent_stats = agent.get_stats()
        
        click.echo("\nSpeculum Principis Statistics")
        click.echo("=" * 40)
        
        click.echo("\nDatabase:")
        click.echo(f"  Total content items: {db_stats.get('total_content_items', 0)}")
        click.echo(f"  Total subjects: {db_stats.get('total_subjects', 0)}")
        click.echo(f"  Recent content (7 days): {db_stats.get('recent_content_items', 0)}")
        click.echo(f"  Recent subjects (7 days): {db_stats.get('recent_subjects', 0)}")
        
        click.echo("\nAgent:")
        click.echo(f"  Status: {'Running' if agent_stats['is_running'] else 'Stopped'}")
        click.echo(f"  Total runs: {agent_stats['total_runs']}")
        click.echo(f"  Content analyzed: {agent_stats['total_content_analyzed']}")
        click.echo(f"  Subjects found: {agent_stats['total_subjects_found']}")
        click.echo(f"  Errors: {agent_stats['errors']}")
        
        if agent_stats['last_run']:
            last_run = datetime.fromisoformat(agent_stats['last_run'])
            click.echo(f"  Last run: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        asyncio.run(show_stats())
    except Exception as e:
        click.echo(f"Error getting statistics: {e}", err=True)


@main.command()
@click.option('--source-type', type=click.Choice(['rss', 'web']), required=True, help='Type of source to add')
@click.option('--name', required=True, help='Name for the source')
@click.option('--url', required=True, help='URL of the source')
@click.option('--selector', help='CSS selector for web scraping (required for web sources)')
@click.pass_context
def add_source(ctx, source_type: str, name: str, url: str, selector: Optional[str]):
    """Add a new monitoring source."""
    config = ctx.obj['config']
    
    if source_type == 'web' and not selector:
        click.echo("CSS selector is required for web sources.", err=True)
        return
    
    async def add_new_source():
        agent = SpeculumAgent(config)
        
        if source_type == 'rss':
            agent.source_manager.add_rss_source(name, url)
            click.echo(f"Added RSS source: {name} ({url})")
        else:
            agent.source_manager.add_web_source(name, url, selector)
            click.echo(f"Added web source: {name} ({url}) with selector: {selector}")
    
    try:
        asyncio.run(add_new_source())
    except Exception as e:
        click.echo(f"Error adding source: {e}", err=True)


@main.command()
@click.pass_context
def test(ctx):
    """Run a test monitoring cycle."""
    config = ctx.obj['config']
    click.echo("Running test monitoring cycle...")
    
    async def test_cycle():
        agent = SpeculumAgent(config)
        await agent.db_manager.initialize()
        
        # Run a single monitoring cycle
        result = await agent._run_monitoring_cycle()
        
        click.echo(f"\nTest cycle completed:")
        click.echo(f"  Sources checked: {result.sources_checked}")
        click.echo(f"  Content items found: {result.content_items_found}")
        click.echo(f"  Relevant subjects: {result.relevant_subjects}")
        
        if result.errors:
            click.echo(f"  Errors: {len(result.errors)}")
            for error in result.errors:
                click.echo(f"    - {error}")
    
    try:
        asyncio.run(test_cycle())
    except Exception as e:
        click.echo(f"Error running test cycle: {e}", err=True)


if __name__ == '__main__':
    main()