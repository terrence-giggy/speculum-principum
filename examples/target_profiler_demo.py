#!/usr/bin/env python3
"""
Target Profiler Agent Demonstration Script

This script demonstrates the Target Profiler Agent's capabilities
for organizational analysis and stakeholder mapping.
"""

import sys
import os
import json
from typing import Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.specialist_agents.target_profiler import TargetProfilerAgent


def main():
    """Demonstrate Target Profiler Agent functionality"""
    
    print("=" * 80)
    print("TARGET PROFILER AGENT DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Configuration
    config = {
        'github_token': os.getenv('GITHUB_TOKEN', 'demo_token'),
        'ai': {
            'model': 'gpt-4o',
            'timeout': 60,
            'max_retries': 3
        }
    }
    
    # Initialize Target Profiler Agent
    print("1. Initializing Target Profiler Agent...")
    agent = TargetProfilerAgent(config=config)
    
    print(f"   ✓ Agent Type: {agent.specialist_type.value}")
    print(f"   ✓ Supported Labels: {len(agent.supported_labels)} labels")
    print(f"   ✓ Required Capabilities: {len(agent.required_capabilities)} capabilities")
    print()
    
    # Sample organizational analysis issue
    organizational_issue = {
        'number': 789,
        'title': 'Strategic Assessment: GlobalTech Enterprises Organizational Structure',
        'body': '''
        ORGANIZATIONAL INTELLIGENCE BRIEF
        
        EXECUTIVE SUMMARY:
        GlobalTech Enterprises is a multinational technology corporation with significant 
        market presence requiring comprehensive organizational analysis.
        
        LEADERSHIP STRUCTURE:
        • Chief Executive Officer: Alexandra Chen (5 years tenure)
        • Chief Technology Officer: Marcus Rodriguez (3 years tenure) 
        • Chief Financial Officer: Jennifer Kim (2 years tenure)
        • VP of Operations: David Thompson (7 years tenure)
        • VP of Strategic Partnerships: Sarah Williams (1 year tenure)
        
        ORGANIZATIONAL DIVISIONS:
        • Technology Development Division (2,500 employees)
          - AI/ML Research Group (300 researchers)
          - Cloud Infrastructure Team (450 engineers)
          - Cybersecurity Unit (200 specialists)
          
        • Business Operations Division (1,200 employees)  
          - Sales Organization (600 representatives)
          - Marketing Department (300 specialists)
          - Customer Success Team (300 managers)
          
        • Corporate Functions (800 employees)
          - Human Resources (150 staff)
          - Finance & Accounting (200 staff)
          - Legal & Compliance (100 lawyers)
          - Facilities & IT Support (350 staff)
        
        FINANCIAL PROFILE:
        • Annual Revenue: $2.8 billion (2023)
        • R&D Investment: $420 million (15% of revenue)
        • Market Capitalization: $18 billion
        • Recent Series D Funding: $200 million (Q2 2023)
        • Primary Revenue Streams: Enterprise software licensing, cloud services, consulting
        
        STRATEGIC PARTNERSHIPS:
        • Microsoft Azure - Cloud infrastructure partnership
        • Amazon Web Services - Multi-cloud strategy implementation
        • Salesforce - CRM integration and business applications
        • Oracle - Enterprise database and analytics solutions
        • IBM - AI and machine learning collaboration
        
        COMPETITIVE POSITIONING:
        • Primary Competitors: Salesforce, ServiceNow, Workday
        • Market Share: 12% in enterprise software automation
        • Competitive Advantages: AI-driven automation, vertical market specialization
        • Market Challenges: Increasing competition, rapid technology evolution
        
        RISK FACTORS:
        • Leadership transition risk (new VP Strategic Partnerships)
        • Technology disruption from emerging AI competitors
        • Regulatory compliance in multiple international markets
        • Cybersecurity threats to intellectual property
        • Economic sensitivity in enterprise software spending
        
        DECISION-MAKING STRUCTURE:
        • Executive Committee: CEO + C-Suite (monthly strategic decisions)
        • Technical Review Board: CTO + Engineering VPs (weekly technical decisions)
        • Investment Committee: CEO + CFO + Board Members (quarterly investment decisions)
        • Partnership Committee: VP Strategic Partnerships + Business Units (monthly partnership decisions)
        ''',
        'labels': [
            {'name': 'organizational'},
            {'name': 'business'},
            {'name': 'strategic'},
            {'name': 'corporate'},
            {'name': 'leadership'},
            {'name': 'financial-analysis'}
        ],
        'created_at': '2024-01-20T09:00:00Z',
        'updated_at': '2024-01-20T09:30:00Z'
    }
    
    # Test compatibility
    print("2. Testing Issue Compatibility...")
    is_compatible = agent.validate_issue_compatibility(organizational_issue)
    print(f"   ✓ Organizational Issue Compatible: {is_compatible}")
    
    # Test priority calculation
    priority = agent.calculate_priority(organizational_issue)
    print(f"   ✓ Analysis Priority Score: {priority}/10")
    print()
    
    # Perform organizational analysis
    print("3. Performing Organizational Analysis...")
    print("   [This is a demonstration - AI client will be mocked]")
    
    # Mock AI client for demo (since we don't have real API access)
    from unittest.mock import Mock
    from clients.github_models_client import AIResponse
    
    mock_ai_response = AIResponse(
        content='''{
            "summary": "GlobalTech Enterprises demonstrates a well-structured multinational technology organization with strong leadership, diversified revenue streams, and strategic market positioning. The company shows organizational maturity with clear hierarchical structure, substantial R&D investment, and strategic partnerships with major technology vendors.",
            "key_findings": [
                "Experienced executive leadership team with CEO Alexandra Chen providing stable 5-year leadership",
                "Well-organized divisional structure with clear separation between technology development, business operations, and corporate functions",
                "Strong financial performance with $2.8B annual revenue and 15% R&D investment demonstrating commitment to innovation",
                "Strategic partnerships with major cloud and enterprise software providers creating competitive advantages",
                "Comprehensive decision-making structure with executive committee, technical review board, and specialized committees",
                "Diversified revenue streams across enterprise software licensing, cloud services, and consulting reducing market risk"
            ],
            "recommendations": [
                "Monitor leadership transition risk with new VP of Strategic Partnerships - ensure proper knowledge transfer and relationship continuity",
                "Assess cybersecurity posture given intellectual property risks and large technology workforce",
                "Evaluate competitive positioning against emerging AI-driven automation competitors",
                "Analyze decision-making efficiency across multiple committees and potential optimization opportunities",
                "Consider succession planning for key leadership roles, particularly long-tenured VP of Operations"
            ],
            "organizations": [
                "GlobalTech Enterprises",
                "Microsoft Azure", 
                "Amazon Web Services",
                "Salesforce",
                "Oracle",
                "IBM",
                "ServiceNow",
                "Workday"
            ],
            "stakeholders": [
                "Alexandra Chen (CEO)",
                "Marcus Rodriguez (CTO)", 
                "Jennifer Kim (CFO)",
                "David Thompson (VP Operations)",
                "Sarah Williams (VP Strategic Partnerships)"
            ],
            "relationships": [
                "CEO-CTO strategic technology leadership",
                "CEO-CFO financial and investment oversight",
                "CTO-Engineering VPs technical decision making",
                "VP Strategic Partnerships-Business Units partnership coordination"
            ],
            "financial_indicators": [
                "revenue",
                "investment", 
                "funding",
                "capitalization",
                "licensing"
            ],
            "organizational_levels": 4,
            "risk_assessment": {
                "organizational_risk": "low",
                "leadership_risk": "medium", 
                "competitive_risk": "medium"
            },
            "confidence": 0.92
        }''',
        model="gpt-4o",
        usage={"prompt_tokens": 450, "completion_tokens": 320}
    )
    
    agent.ai_client = Mock()
    agent.ai_client.chat_completion.return_value = mock_ai_response
    agent.ai_client.model = "gpt-4o"
    
    # Perform analysis
    analysis_result = agent.analyze_issue(organizational_issue)
    
    print(f"   ✓ Analysis Status: {analysis_result.status.value}")
    print(f"   ✓ Confidence Score: {analysis_result.confidence_score:.2f}")
    print(f"   ✓ Organizations Identified: {len(analysis_result.entities_analyzed)}")
    print(f"   ✓ Key Findings: {len(analysis_result.key_findings)}")
    print(f"   ✓ Recommendations: {len(analysis_result.recommendations)}")
    print()
    
    # Display analysis results
    print("4. Analysis Results Summary:")
    print("-" * 40)
    print(f"Summary: {analysis_result.summary[:150]}...")
    print()
    
    print("Key Organizations Identified:")
    for i, org in enumerate(analysis_result.entities_analyzed[:5], 1):
        print(f"  {i}. {org}")
    print()
    
    print("Critical Findings:")
    for i, finding in enumerate(analysis_result.key_findings[:3], 1):
        print(f"  {i}. {finding}")
    print()
    
    print("Strategic Recommendations:")
    for i, rec in enumerate(analysis_result.recommendations[:3], 1):
        print(f"  {i}. {rec}")
    print()
    
    # Risk assessment
    if analysis_result.risk_assessment:
        print("Risk Assessment:")
        for risk_type, level in analysis_result.risk_assessment.items():
            print(f"  • {risk_type.replace('_', ' ').title()}: {level.upper()}")
        print()
    
    # Technical details
    print("5. Technical Analysis Details:")
    print("-" * 40)
    print(f"Analysis ID: {analysis_result.analysis_id}")
    print(f"Specialist Type: {analysis_result.specialist_type.value}")
    print(f"Processing Method: {analysis_result.specialist_notes.get('analysis_type', 'N/A')}")
    print(f"Model Used: {analysis_result.specialist_notes.get('model_used', 'N/A')}")
    print(f"Stakeholder Count: {analysis_result.specialist_notes.get('stakeholder_count', 0)}")
    print(f"Organizational Levels: {analysis_result.specialist_notes.get('organizational_levels', 1)}")
    print()
    
    # Test with non-organizational content
    print("6. Testing Non-Organizational Content...")
    
    technical_issue = {
        'number': 790,
        'title': 'Database Performance Issue: Query Optimization Needed',
        'body': '''
        Database queries are running slowly on the user table.
        Need to optimize the following query:
        
        SELECT * FROM users WHERE created_at > '2024-01-01'
        ORDER BY created_at DESC LIMIT 1000;
        
        Current execution time: 15 seconds
        Expected: < 2 seconds
        ''',
        'labels': [
            {'name': 'database'},
            {'name': 'performance'},
            {'name': 'technical'}
        ]
    }
    
    is_tech_compatible = agent.validate_issue_compatibility(technical_issue)
    tech_priority = agent.calculate_priority(technical_issue)
    
    print(f"   ✓ Technical Issue Compatible: {is_tech_compatible}")
    print(f"   ✓ Technical Issue Priority: {tech_priority}/10")
    print()
    
    print("7. Demonstration Complete!")
    print("-" * 40)
    print("Target Profiler Agent successfully demonstrated:")
    print("  • Organizational content detection and compatibility assessment")
    print("  • Priority scoring based on business intelligence indicators")
    print("  • Comprehensive organizational analysis with stakeholder mapping")
    print("  • Strategic risk assessment and actionable recommendations")
    print("  • Integration with AI-enhanced analysis capabilities")
    print()
    print("The Target Profiler Agent is ready for organizational intelligence operations.")


if __name__ == "__main__":
    main()