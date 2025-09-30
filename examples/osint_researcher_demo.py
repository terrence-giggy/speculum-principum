#!/usr/bin/env python3
"""
OSINT Researcher Agent Demonstration

This script demonstrates the capabilities of the OSINT Researcher specialist agent,
showing how it analyzes GitHub issues for OSINT research opportunities, conducts
digital footprint assessments, and provides verification recommendations.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from datetime import datetime
from typing import Dict, Any

# Import the OSINT Researcher Agent
from src.agents.specialist_agents.osint_researcher import OSINTResearcherAgent
from src.agents.specialist_agents import SpecialistType, AnalysisStatus


def create_sample_osint_issue() -> Dict[str, Any]:
    """Create a sample GitHub issue with OSINT-relevant content."""
    return {
        'number': 456,
        'title': 'Digital Footprint Analysis: Competitor Intelligence Research',
        'body': '''
# OSINT Research Request

## Objective
Conduct comprehensive digital footprint analysis of target organization "TechCorp Solutions" to support competitive intelligence gathering.

## Specific Requirements

### Digital Footprint Assessment
- Domain analysis: techcorp-solutions.com and associated subdomains
- Social media presence mapping across LinkedIn, Twitter, and Facebook
- Technical infrastructure reconnaissance (hosting, DNS, CDN analysis)
- Employee identification and public profile analysis

### Verification Priorities
- Validate executive leadership information from public sources
- Cross-reference company registration and public records
- Verify technical infrastructure claims and capabilities
- Assess credibility of published case studies and client testimonials

### Research Scope
- **Primary Domain**: techcorp-solutions.com
- **Key Personnel**: CEO John Smith, CTO Sarah Johnson
- **Technologies**: Cloud hosting, AI/ML capabilities, cybersecurity solutions
- **Locations**: Headquarters in Austin, TX; satellite office in Denver, CO
- **Public Contacts**: info@techcorp-solutions.com, (555) 123-4567

## Intelligence Gaps
- Missing information on recent partnerships or acquisitions
- Unclear technical architecture and security posture
- Limited visibility into actual client base beyond marketing claims
- No information on upcoming product releases or strategic direction

## Sources to Verify
- Company website claims about 100+ enterprise clients
- LinkedIn profiles showing 50+ employees
- Recent press releases about $5M Series A funding
- Technology blog posts claiming industry expertise
        ''',
        'labels': [
            {'name': 'osint'},
            {'name': 'reconnaissance'},
            {'name': 'digital-footprint'},
            {'name': 'verification'},
            {'name': 'competitive-intelligence'}
        ],
        'assignees': [{'login': 'github-copilot[bot]'}],
        'created_at': '2024-01-15T09:30:00Z',
        'updated_at': '2024-01-15T09:30:00Z',
        'url': 'https://github.com/demo/repo/issues/456'
    }


def create_sample_extracted_content() -> Dict[str, Any]:
    """Create sample structured content extracted from the OSINT issue."""
    return {
        'entities': {
            'organization': [
                {'name': 'TechCorp Solutions', 'confidence': 0.95, 'type': 'organization'},
                {'name': 'Austin TX', 'confidence': 0.9, 'type': 'location'},
                {'name': 'Denver CO', 'confidence': 0.9, 'type': 'location'}
            ],
            'person': [
                {'name': 'John Smith', 'confidence': 0.8, 'type': 'person'},
                {'name': 'Sarah Johnson', 'confidence': 0.8, 'type': 'person'}
            ],
            'domain': [
                {'name': 'techcorp-solutions.com', 'confidence': 0.95, 'type': 'domain'},
                {'name': 'info@techcorp-solutions.com', 'confidence': 0.9, 'type': 'email'}
            ],
            'technology': [
                {'name': 'AI/ML capabilities', 'confidence': 0.7, 'type': 'technology'},
                {'name': 'Cloud hosting', 'confidence': 0.8, 'type': 'technology'},
                {'name': 'Cybersecurity solutions', 'confidence': 0.8, 'type': 'technology'}
            ]
        },
        'relationships': [
            {
                'entity1': 'John Smith',
                'entity2': 'TechCorp Solutions',
                'relationship': 'CEO of',
                'confidence': 0.9
            },
            {
                'entity1': 'Sarah Johnson',
                'entity2': 'TechCorp Solutions',
                'relationship': 'CTO of',
                'confidence': 0.9
            },
            {
                'entity1': 'TechCorp Solutions',
                'entity2': 'techcorp-solutions.com',
                'relationship': 'owns',
                'confidence': 0.95
            }
        ],
        'events': [
            {
                'description': 'Series A funding round',
                'timestamp': '2024-01-01',
                'entities_involved': ['TechCorp Solutions'],
                'confidence': 0.7
            }
        ],
        'indicators': [
            {
                'type': 'domain',
                'value': 'techcorp-solutions.com',
                'description': 'Primary target domain for OSINT analysis',
                'confidence': 0.95
            },
            {
                'type': 'email',
                'value': 'info@techcorp-solutions.com',
                'description': 'Primary contact email address',
                'confidence': 0.9
            }
        ]
    }


def demonstrate_osint_analysis():
    """Demonstrate OSINT researcher analysis capabilities."""
    print("🔍 OSINT Researcher Agent Demonstration")
    print("=" * 50)
    print()
    
    # Initialize OSINT Researcher Agent
    print("📋 Initializing OSINT Researcher Agent...")
    osint_agent = OSINTResearcherAgent()
    
    # Display agent properties
    print(f"✓ Specialist Type: {osint_agent.specialist_type.value}")
    print(f"✓ Supported Labels: {', '.join(osint_agent.supported_labels[:5])}... ({len(osint_agent.supported_labels)} total)")
    print(f"✓ Required Capabilities: {', '.join(osint_agent.required_capabilities)}")
    print()
    
    # Create sample data
    print("📄 Preparing Sample OSINT Issue...")
    issue_data = create_sample_osint_issue()
    structured_content = create_sample_extracted_content()
    
    print(f"✓ Issue #{issue_data['number']}: {issue_data['title']}")
    print(f"✓ Labels: {', '.join([label['name'] for label in issue_data['labels']])}")
    print(f"✓ Extracted Entities: {sum(len(entities) for entities in structured_content['entities'].values())} total")
    print()
    
    # Test issue compatibility
    print("🎯 Testing Issue Compatibility...")
    is_compatible = osint_agent.validate_issue_compatibility(issue_data)
    priority_score = osint_agent.calculate_priority_score(issue_data)
    
    print(f"✓ Compatibility: {'✅ Compatible' if is_compatible else '❌ Not Compatible'}")
    print(f"✓ Priority Score: {priority_score:.2f} (0.0-1.0)")
    print()
    
    if not is_compatible:
        print("❌ Issue is not compatible with OSINT analysis. Exiting demo.")
        return
    
    # Perform OSINT analysis
    print("🔬 Performing OSINT Research Analysis...")
    print("   This may take a moment as we analyze the content...")
    print()
    
    try:
        analysis_result = osint_agent.analyze_issue(issue_data, structured_content)
        
        print("📊 Analysis Results:")
        print("-" * 30)
        print(f"Analysis ID: {analysis_result.analysis_id}")
        print(f"Status: {analysis_result.status.value}")
        print(f"Confidence Score: {analysis_result.confidence_score:.2f}")
        print(f"Processing Method: {analysis_result.specialist_notes.get('processing_method', 'Unknown')}")
        print()
        
        print("🎯 Key Findings:")
        for i, finding in enumerate(analysis_result.key_findings, 1):
            print(f"   {i}. {finding}")
        print()
        
        print("📋 Recommendations:")
        for i, recommendation in enumerate(analysis_result.recommendations, 1):
            print(f"   {i}. {recommendation}")
        print()
        
        # Display detailed OSINT analysis if available
        if 'osint_analysis' in analysis_result.specialist_notes:
            osint_data = analysis_result.specialist_notes['osint_analysis']
            
            print("🌐 Digital Footprint Assessment:")
            df_assessment = osint_data.get('findings', {}).get('digital_footprint', {})
            print(f"   Assessment: {df_assessment.get('assessment', 'Not assessed')}")
            if df_assessment.get('opportunities'):
                print("   Opportunities:")
                for opp in df_assessment['opportunities'][:3]:  # Show top 3
                    print(f"     • {opp}")
            print()
            
            print("🔍 Verification Status:")
            verification = osint_data.get('findings', {}).get('verification_status', {})
            requires_verification = verification.get('requires_verification', [])
            if requires_verification:
                print("   Entities requiring verification:")
                for entity in requires_verification[:3]:  # Show top 3
                    print(f"     ⚠️ {entity}")
            else:
                print("   ✅ No critical verification issues identified")
            print()
            
            print("📈 Confidence Assessment:")
            confidence = osint_data.get('confidence_assessment', {})
            print(f"   Overall: {confidence.get('overall', 0) * 100:.0f}%")
            print(f"   Source Reliability: {confidence.get('source_reliability', 0) * 100:.0f}%")
            print(f"   Information Completeness: {confidence.get('information_completeness', 0) * 100:.0f}%")
            print()
            
            print("🔗 OSINT Collection Techniques:")
            techniques = osint_data.get('recommendations', {}).get('research_techniques', [])
            for technique in techniques[:4]:  # Show top 4
                print(f"   • {technique}")
            print()
        
        print("⏱️ Processing Performance:")
        print(f"   Entities Analyzed: {len(analysis_result.entities_analyzed)}")
        print(f"   Created: {analysis_result.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if analysis_result.processing_time_seconds:
            print(f"   Processing Time: {analysis_result.processing_time_seconds:.2f} seconds")
        print()
        
        print("✅ OSINT Analysis Complete!")
        print()
        print("📝 Summary:")
        print(f"   The OSINT Researcher Agent successfully analyzed issue #{issue_data['number']}")
        print(f"   and identified {len(structured_content['entities']['domain'])} digital entities for further research.")
        print(f"   Priority verification targets include personnel and organizational claims.")
        print(f"   Recommended OSINT techniques include domain analysis, social media research,")
        print(f"   and public records verification to validate the target organization's profile.")
        
    except Exception as e:
        print(f"❌ Analysis failed with error: {e}")
        return
    
    print()
    print("🎉 OSINT Researcher Agent demonstration completed successfully!")
    print("   This agent specializes in:")
    print("   • Digital footprint analysis and reconnaissance")
    print("   • Information verification and source credibility assessment")  
    print("   • Research gap identification and collection planning")
    print("   • Cross-reference validation with multiple sources")
    print()
    print("   For production use, configure with proper AI credentials and")
    print("   integrate with the full issue processing pipeline.")


if __name__ == "__main__":
    demonstrate_osint_analysis()