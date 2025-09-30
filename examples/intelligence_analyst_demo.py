#!/usr/bin/env python3
"""
Intelligence Analyst Agent Demo

This script demonstrates the Intelligence Analyst Agent functionality
including issue analysis, threat assessment, and professional reporting.

Usage:
    python examples/intelligence_analyst_demo.py
"""

import sys
import json
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.specialist_agents.intelligence_analyst import IntelligenceAnalystAgent


def create_sample_intelligence_issue():
    """Create a sample intelligence issue for demonstration."""
    return {
        'number': 101,
        'title': 'APT29 Campaign Analysis - Government Infrastructure Targeting',
        'body': '''
# Threat Intelligence Report: APT29 Active Campaign

## Overview
Recent intelligence indicates that APT29 (Cozy Bear), a Russian state-sponsored 
advanced persistent threat group, has initiated a new campaign targeting 
government infrastructure and election-related systems.

## Key Indicators
- **Domain**: election-malware.net (confirmed malicious)
- **IP Address**: 185.220.101.55 (command and control server)
- **Hash**: e3b0c44298fc1c149afbf4c8996fb924 (trojan payload)

## Attack Vectors
- Spear phishing emails with malicious attachments
- Credential harvesting through fake login portals  
- Supply chain compromise targeting software vendors
- Zero-day exploits against unpatched systems

## Strategic Context
This campaign appears coordinated with Russian geopolitical objectives,
particularly related to election interference and intelligence collection
on government policy development.

## Immediate Concerns  
- **CRITICAL**: Active targeting of election infrastructure
- **HIGH**: Potential data exfiltration from government networks
- **URGENT**: Need for immediate defensive measures and attribution

## Recommended Actions
Intelligence analysis required to assess:
1. Full scope of the campaign and targeted entities
2. Attribution confidence and supporting evidence
3. Strategic implications for national security
4. Recommended defensive and diplomatic responses
        ''',
        'labels': [
            {'name': 'intelligence'},
            {'name': 'intelligence-analyst'},
            {'name': 'threat-assessment'},
            {'name': 'apt'},
            {'name': 'strategic-intelligence'},
            {'name': 'urgent'},
            {'name': 'geopolitical'}
        ],
        'assignee': 'github-copilot[bot]',
        'created_at': '2024-12-27T15:30:00Z'
    }


def create_sample_extracted_content():
    """Create sample extracted content to demonstrate AI integration."""
    return {
        'entities': [
            {'name': 'APT29', 'type': 'threat_actor', 'confidence': 0.95},
            {'name': 'Cozy Bear', 'type': 'threat_actor', 'confidence': 0.92},
            {'name': 'Russian', 'type': 'nation_state', 'confidence': 0.88},
            {'name': 'election-malware.net', 'type': 'domain', 'confidence': 0.90},
            {'name': '185.220.101.55', 'type': 'ip_address', 'confidence': 0.87},
            {'name': 'government infrastructure', 'type': 'target', 'confidence': 0.85},
            {'name': 'election systems', 'type': 'target', 'confidence': 0.83}
        ],
        'relationships': [
            {
                'source': 'APT29',
                'target': 'Cozy Bear',
                'type': 'alias_of',
                'confidence': 0.95
            },
            {
                'source': 'APT29',
                'target': 'Russian',
                'type': 'attributed_to',
                'confidence': 0.88
            },
            {
                'source': 'APT29',
                'target': 'government infrastructure',
                'type': 'targets',
                'confidence': 0.85
            },
            {
                'source': 'election-malware.net',
                'target': '185.220.101.55',
                'type': 'resolves_to',
                'confidence': 0.90
            }
        ],
        'events': [
            {
                'description': 'Campaign initiation detected',
                'timestamp': '2024-12-20',
                'type': 'attack_campaign',
                'confidence': 0.82
            },
            {
                'description': 'Government infrastructure targeting observed',
                'timestamp': '2024-12-22',
                'type': 'targeting_activity',
                'confidence': 0.78
            }
        ],
        'indicators': [
            {'value': 'election-malware.net', 'type': 'domain', 'confidence': 0.90},
            {'value': '185.220.101.55', 'type': 'ip_address', 'confidence': 0.87},
            {'value': 'e3b0c44298fc1c149afbf4c8996fb924', 'type': 'hash', 'confidence': 0.85}
        ],
        'confidence_score': 0.86
    }


def demonstrate_intelligence_analysis():
    """Demonstrate the Intelligence Analyst Agent functionality."""
    
    print("🎯 Intelligence Analyst Agent Demonstration")
    print("=" * 60)
    
    # Create sample data
    issue_data = create_sample_intelligence_issue()
    extracted_content = create_sample_extracted_content()
    
    print(f"\n📋 Sample Issue: #{issue_data['number']}")
    print(f"Title: {issue_data['title']}")
    print(f"Labels: {[label['name'] for label in issue_data['labels']]}")
    
    # Initialize Intelligence Analyst (without AI client for demo)
    print(f"\n🤖 Initializing Intelligence Analyst Agent...")
    config = {
        # No github_token - will use fallback analysis
        'ai': {
            'model': 'gpt-4o',
            'timeout': 30
        }
    }
    
    analyst = IntelligenceAnalystAgent(config=config)
    
    # Validate issue compatibility
    print(f"\n✅ Validating Issue Compatibility...")
    is_compatible = analyst.validate_issue_compatibility(issue_data)
    print(f"Compatible for intelligence analysis: {is_compatible}")
    
    if is_compatible:
        # Calculate priority
        priority = analyst.get_analysis_priority(issue_data)
        print(f"Analysis priority score: {priority}/100")
        
        # Perform analysis
        print(f"\n🔍 Performing Intelligence Analysis...")
        analysis_result = analyst.analyze_issue(issue_data, extracted_content)
        
        # Display results
        print(f"\n📊 Analysis Results:")
        print(f"Status: {analysis_result.status.value}")
        print(f"Specialist Type: {analysis_result.specialist_type.value}")
        print(f"Analysis ID: {analysis_result.analysis_id}")
        print(f"Confidence Score: {analysis_result.confidence_score:.2f}")
        
        if analysis_result.processing_time_seconds:
            print(f"Processing Time: {analysis_result.processing_time_seconds:.2f} seconds")
        
        print(f"\n📝 Executive Summary:")
        print(f"{analysis_result.summary}")
        
        print(f"\n🔍 Key Findings:")
        for i, finding in enumerate(analysis_result.key_findings, 1):
            print(f"{i}. {finding}")
        
        print(f"\n💡 Recommendations:")
        for i, recommendation in enumerate(analysis_result.recommendations, 1):
            print(f"{i}. {recommendation}")
        
        if analysis_result.risk_assessment:
            print(f"\n⚠️  Risk Assessment:")
            print(f"Threat Level: {analysis_result.risk_assessment.get('threat_level', 'Unknown')}")
            print(f"Impact Level: {analysis_result.risk_assessment.get('impact_level', 'Unknown')}")
        
        # Demonstrate serialization
        print(f"\n💾 Analysis Result (JSON):")
        result_dict = analysis_result.to_dict()
        print(json.dumps(result_dict, indent=2, default=str)[:500] + "...")
        
    else:
        print("❌ Issue is not suitable for intelligence analysis")
    
    print(f"\n🎉 Demonstration Complete!")


def main():
    """Main demonstration function."""
    try:
        demonstrate_intelligence_analysis()
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()