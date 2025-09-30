"""
CLI Integration for Specialist Workflow Configuration

This module provides command-line interface integration for the specialist
workflow configuration system. Implements CLI components for Task 3.3.
"""

import argparse
import json
import sys
from typing import Dict, Any, Optional
from pathlib import Path

from ..workflow.specialist_workflow_config import (
    SpecialistWorkflowConfigManager,
    SpecialistType
)
from ..workflow.specialist_registry import (
    SpecialistWorkflowRegistry,
    SpecialistAssignment
)
from ..utils.logging_config import get_logger, log_exception
from .cli_helpers import ProgressReporter


# Simple print helper functions
def print_success(message: str) -> None:
    """Print success message with green color."""
    print(f"\033[92m{message}\033[0m")


def print_error(message: str) -> None:
    """Print error message with red color."""
    print(f"\033[91m{message}\033[0m", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print warning message with yellow color."""
    print(f"\033[93m{message}\033[0m")


def print_info(message: str) -> None:
    """Print info message with blue color."""
    print(f"\033[94m{message}\033[0m")


def format_table(data: list, headers: list) -> str:
    """Format data as a simple table."""
    if not data:
        return "No data to display"
    
    # Calculate column widths
    col_widths = [len(str(header)) for header in headers]
    for row in data:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Create table
    lines = []
    
    # Header
    header_line = " | ".join(str(headers[i]).ljust(col_widths[i]) for i in range(len(headers)))
    lines.append(header_line)
    lines.append("-" * len(header_line))
    
    # Data rows
    for row in data:
        row_line = " | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))
        lines.append(row_line)
    
    return "\n".join(lines)


def setup_specialist_config_parser(subparsers) -> None:
    """Set up specialist-config command parser."""
    config_parser = subparsers.add_parser(
        'specialist-config',
        help='Manage specialist workflow configurations'
    )
    
    # Subcommands for specialist configuration
    config_subparsers = config_parser.add_subparsers(
        dest='specialist_action',
        help='Specialist configuration actions'
    )
    
    # Validate configuration command
    validate_parser = config_subparsers.add_parser(
        'validate',
        help='Validate specialist workflow configurations'
    )
    validate_parser.add_argument(
        '--config',
        default='config.yaml',
        help='Configuration file path'
    )
    validate_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed validation output'
    )
    
    # Show statistics command
    stats_parser = config_subparsers.add_parser(
        'stats',
        help='Show specialist configuration statistics'
    )
    stats_parser.add_argument(
        '--config',
        default='config.yaml',
        help='Configuration file path'
    )
    stats_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format'
    )
    
    # Test assignment command  
    test_parser = config_subparsers.add_parser(
        'test-assignment',
        help='Test specialist assignment for given labels'
    )
    test_parser.add_argument(
        '--config',
        default='config.yaml',
        help='Configuration file path'
    )
    test_parser.add_argument(
        '--labels',
        nargs='+',
        required=True,
        help='Issue labels to test'
    )
    test_parser.add_argument(
        '--content',
        help='Issue content for keyword matching'
    )
    test_parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.6,
        help='Minimum confidence threshold'
    )
    
    # List specialists command
    list_parser = config_subparsers.add_parser(
        'list',
        help='List available specialists and their configurations'
    )
    list_parser.add_argument(
        '--config',
        default='config.yaml',
        help='Configuration file path'
    )
    list_parser.add_argument(
        '--specialist',
        choices=[st.value for st in SpecialistType],
        help='Show details for specific specialist'
    )
    
    # Export configuration command
    export_parser = config_subparsers.add_parser(
        'export',
        help='Export specialist configuration summary'
    )
    export_parser.add_argument(
        '--config',
        default='config.yaml',
        help='Configuration file path'
    )
    export_parser.add_argument(
        '--output',
        help='Output file path (default: stdout)'
    )
    export_parser.add_argument(
        '--format',
        choices=['json', 'yaml'],
        default='json',
        help='Export format'
    )


def handle_specialist_config_command(args) -> int:
    """
    Handle specialist-config command.
    
    Args:
        args: Parsed command arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger = get_logger(__name__)
    
    try:
        if not args.specialist_action:
            print_error("No specialist configuration action specified")
            return 1
        
        if args.specialist_action == 'validate':
            return _handle_validate_config(args)
        elif args.specialist_action == 'stats':
            return _handle_show_stats(args)
        elif args.specialist_action == 'test-assignment':
            return _handle_test_assignment(args)
        elif args.specialist_action == 'list':
            return _handle_list_specialists(args)
        elif args.specialist_action == 'export':
            return _handle_export_config(args)
        else:
            print_error(f"Unknown specialist configuration action: {args.specialist_action}")
            return 1
            
    except Exception as e:
        log_exception(logger, "Specialist configuration command failed", e)
        print_error(f"Command failed: {e}")
        return 1


def _handle_validate_config(args) -> int:
    """Handle validate configuration command."""
    logger = get_logger(__name__)
    
    try:
        print_info("Validating specialist workflow configurations...")
        
        # Initialize configuration manager
        config_manager = SpecialistWorkflowConfigManager(args.config)
        config_manager.load_configurations()
        
        # Validate configuration
        validation_result = config_manager.validate_configuration()
        
        if validation_result['valid']:
            print_success("✅ All specialist configurations are valid!")
            
            if args.verbose:
                print_info("\n📊 Validation Summary:")
                print_info(f"  • Specialists: {validation_result['specialist_count']}")
                print_info(f"  • Assignment rules: {validation_result['rule_count']}")
                
                if validation_result.get('warnings'):
                    print_warning("\n⚠️  Warnings:")
                    for warning in validation_result['warnings']:
                        print_warning(f"  • {warning}")
        else:
            print_error("❌ Configuration validation failed!")
            
            if validation_result.get('errors'):
                print_error("\n🚨 Errors:")
                for error in validation_result['errors']:
                    print_error(f"  • {error}")
            
            if validation_result.get('warnings'):
                print_warning(f"\n⚠️  Warnings:")
                for warning in validation_result['warnings']:
                    print_warning(f"  • {warning}")
            
            return 1
        
        return 0
        
    except Exception as e:
        log_exception(logger, "Configuration validation failed", e)
        print_error(f"Validation failed: {e}")
        return 1


def _handle_show_stats(args) -> int:
    """Handle show statistics command."""
    logger = get_logger(__name__)
    
    try:
        print_info("Gathering specialist configuration statistics...")
        
        # Initialize registry
        registry = SpecialistWorkflowRegistry(args.config)
        registry.initialize()
        
        # Get statistics
        stats = registry.get_registry_statistics()
        
        if args.format == 'json':
            print(json.dumps(stats, indent=2))
        else:
            _display_stats_table(stats)
        
        return 0
        
    except Exception as e:
        log_exception(logger, "Statistics gathering failed", e)
        print_error(f"Failed to get statistics: {e}")
        return 1


def _display_stats_table(stats: Dict[str, Any]) -> None:
    """Display statistics in table format."""
    print_success("\n📊 Specialist Workflow Registry Statistics")
    print_info(f"Generated: {stats['timestamp']}")
    
    # Overview statistics
    overview_data = [
        ["Total Specialists", stats['total_specialists']],
        ["Total Workflows", stats['total_workflows']],
        ["Mapped Workflows", stats['mapped_workflows']],
        ["Specialists with Workflows", stats['specialists_with_workflows']],
        ["Avg Workflows per Specialist", f"{stats['average_workflows_per_specialist']:.1f}"]
    ]
    
    print_info("\n📈 Overview:")
    print(format_table(overview_data, headers=["Metric", "Value"]))
    
    # Specialist breakdown
    if stats.get('specialist_breakdown'):
        print_info("\n👥 Specialist Breakdown:")
        specialist_data = []
        
        for specialist, details in stats['specialist_breakdown'].items():
            specialist_data.append([
                specialist.replace('-', ' ').title(),
                details['workflow_count'],
                ', '.join(details['workflow_names'][:2]) + ('...' if len(details['workflow_names']) > 2 else ''),
                '✅' if details['configuration_loaded'] else '❌'
            ])
        
        print(format_table(
            specialist_data,
            headers=["Specialist", "Workflows", "Workflow Names", "Config Loaded"]
        ))
    
    # Workflow distribution
    if stats.get('workflow_distribution'):
        print_info("\n🔄 Workflow Distribution:")
        workflow_data = []
        
        for specialist, workflows in stats['workflow_distribution'].items():
            workflow_data.append([
                specialist.replace('-', ' ').title(),
                len(workflows),
                ', '.join(workflows[:3]) + ('...' if len(workflows) > 3 else '')
            ])
        
        print(format_table(
            workflow_data,
            headers=["Specialist", "Count", "Workflows"]
        ))


def _handle_test_assignment(args) -> int:
    """Handle test assignment command."""
    logger = get_logger(__name__)
    
    try:
        print_info(f"Testing specialist assignment for labels: {', '.join(args.labels)}")
        if args.content:
            print_info(f"Content: {args.content[:100]}...")
        
        # Initialize registry
        registry = SpecialistWorkflowRegistry(args.config)
        registry.initialize()
        
        # Test assignment
        assignment = registry.assign_specialist_to_issue(
            issue_labels=args.labels,
            issue_content=args.content,
            min_confidence=args.min_confidence
        )
        
        if assignment:
            print_success(f"\n✅ Specialist Assignment Found!")
            
            assignment_data = [
                ["Specialist Type", assignment.specialist_type.value.replace('-', ' ').title()],
                ["Confidence", f"{assignment.confidence:.2f}"],
                ["Workflow Name", assignment.workflow_name],
                ["Quality Threshold", f"{assignment.quality_threshold:.2f}"],
                ["Trigger Labels", ', '.join(assignment.trigger_labels)],
                ["Recommended Deliverables", ', '.join(assignment.recommended_deliverables)],
                ["Assignment Reason", assignment.assignment_reason]
            ]
            
            print(format_table(assignment_data, headers=["Attribute", "Value"]))
        else:
            print_warning(f"\n⚠️  No specialist assignment found")
            print_info(f"Minimum confidence threshold: {args.min_confidence}")
            
            # Show available specialists and their trigger labels
            config_manager = SpecialistWorkflowConfigManager(args.config)
            config_manager.load_configurations()
            
            print_info(f"\n💡 Available Specialists:")
            for specialist_type in SpecialistType:
                config = config_manager.get_specialist_config(specialist_type)
                if config:
                    all_labels = set()
                    for rule in config.assignment_rules:
                        all_labels.update(rule.trigger_labels)
                    print_info(f"  • {specialist_type.value.replace('-', ' ').title()}: {', '.join(sorted(all_labels))}")
        
        return 0
        
    except Exception as e:
        log_exception(logger, "Assignment testing failed", e)
        print_error(f"Assignment test failed: {e}")
        return 1


def _handle_list_specialists(args) -> int:
    """Handle list specialists command."""
    logger = get_logger(__name__)
    
    try:
        print_info("Loading specialist configurations...")
        
        # Initialize configuration manager
        config_manager = SpecialistWorkflowConfigManager(args.config)
        config_manager.load_configurations()
        
        specialists = config_manager.get_all_specialist_configs()
        
        if args.specialist:
            # Show details for specific specialist
            specialist_type = SpecialistType(args.specialist)
            config = specialists.get(specialist_type)
            
            if not config:
                print_error(f"Specialist '{args.specialist}' not found")
                return 1
            
            _display_specialist_details(config)
        else:
            # List all specialists
            print_success(f"\n👥 Available Specialists ({len(specialists)}):")
            
            for specialist_type, config in specialists.items():
                print_info(f"\n🔸 {config.name} ({specialist_type.value})")
                print_info(f"  Description: {config.description}")
                print_info(f"  Version: {config.version}")
                print_info(f"  Assignment Rules: {len(config.assignment_rules)}")
                print_info(f"  Deliverables: {len(config.deliverable_specs)}")
                print_info(f"  Enabled: {'✅' if config.enabled else '❌'}")
        
        return 0
        
    except Exception as e:
        log_exception(logger, "List specialists failed", e)
        print_error(f"Failed to list specialists: {e}")
        return 1


def _display_specialist_details(config) -> None:
    """Display detailed information about a specialist."""
    print_success(f"\n👤 {config.name} Details")
    print_info(f"Type: {config.specialist_type.value}")
    print_info(f"Description: {config.description}")
    print_info(f"Version: {config.version}")
    print_info(f"Enabled: {'✅' if config.enabled else '❌'}")
    
    if config.persona:
        print_info(f"\n🎭 Persona:")
        print_info(f"  {config.persona}")
    
    # Assignment rules
    if config.assignment_rules:
        print_info(f"\n📋 Assignment Rules ({len(config.assignment_rules)}):")
        for i, rule in enumerate(config.assignment_rules, 1):
            print_info(f"  Rule {i}:")
            print_info(f"    • Trigger Labels: {', '.join(rule.trigger_labels)}")
            print_info(f"    • Content Keywords: {', '.join(rule.content_keywords)}")
            print_info(f"    • Priority Weight: {rule.priority_weight}")
            print_info(f"    • Min Confidence: {rule.min_confidence}")
    
    # Deliverable specifications
    if config.deliverable_specs:
        print_info(f"\n📄 Deliverable Specifications ({len(config.deliverable_specs)}):")
        for spec in config.deliverable_specs:
            print_info(f"  • {spec.title} ({spec.name})")
            print_info(f"    Template: {spec.template_name}")
            print_info(f"    Quality Threshold: {spec.quality_threshold}")
            print_info(f"    AI Enhanced: {'✅' if spec.ai_enhanced else '❌'}")
            print_info(f"    Required Sections: {', '.join(spec.required_sections[:3])}{'...' if len(spec.required_sections) > 3 else ''}")
    
    # Quality requirements
    qr = config.quality_requirements
    print_info(f"\n🎯 Quality Requirements:")
    print_info(f"  • Min Confidence Score: {qr.min_confidence_score}")
    print_info(f"  • Require Source References: {'✅' if qr.require_source_references else '❌'}")
    print_info(f"  • Min Word Count: {qr.min_word_count}")
    print_info(f"  • Max Processing Time: {qr.max_processing_time_minutes} minutes")
    print_info(f"  • Validation Strictness: {qr.validation_strictness}")
    
    # AI configuration
    if config.ai_config:
        print_info(f"\n🤖 AI Configuration:")
        for key, value in config.ai_config.items():
            print_info(f"  • {key.replace('_', ' ').title()}: {value}")


def _handle_export_config(args) -> int:
    """Handle export configuration command."""
    logger = get_logger(__name__)
    
    try:
        print_info("Exporting specialist configuration...")
        
        # Initialize configuration manager
        config_manager = SpecialistWorkflowConfigManager(args.config)
        config_manager.load_configurations()
        
        # Export configuration summary
        summary = config_manager.export_configuration_summary()
        
        if args.format == 'json':
            output_text = json.dumps(summary, indent=2)
        else:
            # YAML format
            import yaml
            output_text = yaml.dump(summary, default_flow_style=False, indent=2)
        
        if args.output:
            # Write to file
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(output_text)
            
            print_success(f"Configuration exported to: {output_path}")
        else:
            # Print to stdout
            print(output_text)
        
        return 0
        
    except Exception as e:
        log_exception(logger, "Configuration export failed", e)
        print_error(f"Export failed: {e}")
        return 1


# Integration with main CLI
def add_specialist_config_commands(parser: argparse.ArgumentParser) -> None:
    """
    Add specialist configuration commands to main parser.
    
    Args:
        parser: Main argument parser
    """
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    setup_specialist_config_parser(subparsers)