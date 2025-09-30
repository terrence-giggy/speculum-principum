#!/usr/bin/env python3
"""
AI-Enhanced Deliverable Generator Demo

This script demonstrates the AI-Enhanced Deliverable Generator capabilities:
- Basic deliverable generation without AI
- AI-enhanced content generation with specialist integration
- Quality validation and content improvement
- Specialist analysis integration

Run this script to see how the AI-enhanced deliverable generator works
with both fallback mode and full AI enhancement.
"""

import sys
import os
from datetime import datetime, timezone
from typing import Dict, Any

# Add src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from workflow.ai_enhanced_deliverable_generator import AIEnhancedDeliverableGenerator, ContentType
from workflow.deliverable_generator import DeliverableSpec
from workflow.workflow_matcher import WorkflowInfo
from agents.specialist_agents import AnalysisResult, SpecialistType


class MockIssue:
    """Mock GitHub issue for demo purposes"""
    def __init__(self, number: int, title: str, body: str, labels: list):
        self.number = number
        self.title = title
        self.body = body
        self.labels = [type('Label', (), {'name': label}) for label in labels]
        self.url = f"https://github.com/test/repo/issues/{number}"
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


def create_demo_issue() -> MockIssue:
    """Create a demo issue for testing"""
    return MockIssue(
        number=42,
        title="Critical Infrastructure Security Assessment",
        body="""
        Urgent security assessment required for critical infrastructure components.
        
        **Scope:**
        - Network security analysis
        - Threat modeling and risk assessment
        - OSINT research on potential exposure
        - Vulnerability identification and remediation planning
        
        **Priority:** High
        **Timeline:** 48 hours
        
        This assessment is critical for maintaining operational security
        and protecting against advanced persistent threats.
        """,
        labels=["security", "critical", "intelligence", "infrastructure"]
    )


def create_demo_deliverable_spec() -> DeliverableSpec:
    """Create demo deliverable specification"""
    return DeliverableSpec(
        name="security_intelligence_assessment",
        title="Security Intelligence Assessment Report",
        description="Comprehensive security analysis with AI-enhanced content generation",
        template="intelligence_assessment",
        type="intelligence",
        format="markdown",
        sections=["executive_summary", "threat_analysis", "recommendations", "risk_assessment"]
    )


def create_demo_workflow_info() -> WorkflowInfo:
    """Create demo workflow information"""
    return WorkflowInfo(
        path="/demo/security-workflow.yaml",
        name="security-intelligence-workflow",
        description="AI-enhanced security intelligence analysis workflow",
        version="2.0",
        trigger_labels=["security", "intelligence", "critical"],
        deliverables=[
            {
                "name": "security_assessment",
                "template": "intelligence_assessment",
                "ai_enhanced": True
            }
        ],
        processing={
            "ai_enhanced": True,
            "specialist_agents": ["intelligence-analyst", "osint-researcher"],
            "quality_validation": True
        },
        validation={
            "quality_threshold": 0.8,
            "completeness_check": True,
            "professional_standards": True
        },
        output={
            "format": "markdown",
            "include_metadata": True,
            "quality_report": True
        }
    )


def create_demo_specialist_results() -> Dict[SpecialistType, AnalysisResult]:
    """Create demo specialist analysis results"""
    return {
        SpecialistType.INTELLIGENCE_ANALYST: AnalysisResult(
            specialist_type=SpecialistType.INTELLIGENCE_ANALYST,
            issue_number=42,
            analysis_id="intel_42_demo_001",
            summary="Critical security vulnerabilities identified in infrastructure requiring immediate attention and comprehensive remediation",
            key_findings=[
                "Multiple critical vulnerabilities in network perimeter defenses",
                "Outdated security monitoring systems with limited threat detection",
                "Insufficient network segmentation allowing lateral movement",
                "Weak authentication mechanisms in critical systems",
                "Lack of comprehensive incident response procedures"
            ],
            recommendations=[
                "Implement immediate network perimeter hardening",
                "Deploy advanced threat detection and response systems", 
                "Establish comprehensive network segmentation strategy",
                "Upgrade authentication systems with multi-factor authentication",
                "Develop and test incident response playbooks",
                "Conduct regular penetration testing and vulnerability assessments"
            ],
            confidence_score=0.94,
            indicators=[
                "outdated_firewall_rules",
                "unpatched_systems", 
                "weak_passwords",
                "insufficient_monitoring"
            ],
            entities_analyzed=[
                "network_infrastructure",
                "security_systems",
                "authentication_mechanisms",
                "monitoring_capabilities"
            ],
            specialist_notes={
                "analysis_method": "comprehensive_security_review",
                "tools_used": ["vulnerability_scanners", "network_analysis"],
                "confidence_factors": ["multiple_sources", "cross_validation"],
                "priority_justification": "critical_business_impact"
            }
        ),
        SpecialistType.OSINT_RESEARCHER: AnalysisResult(
            specialist_type=SpecialistType.OSINT_RESEARCHER,
            issue_number=42,
            analysis_id="osint_42_demo_001",
            summary="Significant security exposures identified through open source intelligence gathering and external reconnaissance",
            key_findings=[
                "Publicly exposed configuration files containing sensitive information",
                "Employee social media posts revealing internal security practices",
                "Third-party vendor relationships with questionable security postures",
                "DNS records exposing internal network topology",
                "Historical data breaches affecting similar infrastructure"
            ],
            recommendations=[
                "Immediately remove or secure publicly exposed configuration data",
                "Implement comprehensive social media security awareness training",
                "Conduct thorough security assessments of third-party vendors",
                "Review and sanitize DNS configuration to prevent information leakage",
                "Monitor dark web and breach databases for organizational exposure",
                "Establish external reconnaissance monitoring capabilities"
            ],
            confidence_score=0.88,
            indicators=[
                "exposed_config_files",
                "social_media_disclosure",
                "vendor_vulnerabilities",
                "information_leakage"
            ],
            entities_analyzed=[
                "public_repositories",
                "social_media_profiles",
                "dns_records",
                "third_party_vendors",
                "breach_databases"
            ],
            specialist_notes={
                "sources_verified": 15,
                "verification_confidence": 0.91,
                "collection_methods": ["passive_reconnaissance", "osint_tools"],
                "exposure_severity": "high_risk"
            }
        )
    }


def demo_basic_generation():
    """Demonstrate basic deliverable generation without AI"""
    print("=" * 80)
    print("DEMO 1: Basic Deliverable Generation (No AI)")
    print("=" * 80)
    
    # Create basic generator (no AI token)
    generator = AIEnhancedDeliverableGenerator()
    
    # Create demo data
    issue = create_demo_issue()
    spec = create_demo_deliverable_spec()
    workflow = create_demo_workflow_info()
    
    print(f"AI Enabled: {generator.ai_enabled}")
    print(f"Issue: #{issue.number} - {issue.title}")
    print(f"Deliverable: {spec.name} ({spec.type})")
    print("\n" + "-" * 40)
    
    try:
        # Generate basic deliverable
        content = generator.generate_deliverable(issue, spec, workflow)
        
        print("Generated Content (First 800 characters):")
        print("-" * 40)
        print(content[:800] + "..." if len(content) > 800 else content)
        
        # Generate quality report
        quality_report = generator.generate_quality_report(content, {"issue": issue})
        print(f"\nQuality Metrics:")
        print(f"- Quality Score: {quality_report['quality_score']:.2f}")
        print(f"- Meets Threshold: {quality_report['meets_threshold']}")
        print(f"- Issues Found: {len(quality_report['issues'])}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n")


def demo_ai_enhanced_generation():
    """Demonstrate AI-enhanced deliverable generation (simulated)"""
    print("=" * 80)
    print("DEMO 2: AI-Enhanced Generation (Simulated - No Real API Calls)")
    print("=" * 80)
    
    # Create generator with mock AI capabilities
    generator = AIEnhancedDeliverableGenerator()
    
    # Manually enable AI simulation for demo
    generator.ai_enabled = True
    
    # Create demo data
    issue = create_demo_issue()
    spec = create_demo_deliverable_spec()
    workflow = create_demo_workflow_info()
    specialist_results = create_demo_specialist_results()
    
    print(f"AI Enabled: {generator.ai_enabled}")
    print(f"Issue: #{issue.number} - {issue.title}")
    print(f"Deliverable: {spec.name} ({spec.type})")
    print(f"Specialist Results: {len(specialist_results)} agents")
    print("\n" + "-" * 40)
    
    try:
        # Prepare AI-enhanced context
        context = generator._prepare_ai_enhanced_context(
            issue, spec, workflow, None, specialist_results
        )
        
        print("AI-Enhanced Context Features:")
        print(f"- AI Enhanced: {context['ai_enhanced']}")
        print(f"- Specialist Analysis Available: {'specialist_analysis' in context}")
        print(f"- Recommendations Count: {len(context.get('specialist_recommendations', []))}")
        print("\nSpecialist Analysis Sample:")
        print("-" * 40)
        analysis_sample = context.get('specialist_analysis', '')[:600]
        print(analysis_sample + "..." if len(analysis_sample) >= 600 else analysis_sample)
        
        # Show content generation specs
        print(f"\nContent Generation Capabilities:")
        for content_type in generator.content_specs.keys():
            spec_info = generator.content_specs[content_type]
            print(f"- {content_type.value}: {spec_info.max_tokens} tokens, temp={spec_info.temperature}")
        
        # Demonstrate quality validation
        sample_content = """
# Security Intelligence Assessment Report

## Executive Summary
This comprehensive security intelligence assessment reveals critical vulnerabilities
in the network infrastructure requiring immediate attention and remediation efforts.

## Threat Analysis  
Multiple threat vectors have been identified through specialist analysis including
network perimeter weaknesses, insufficient monitoring, and external exposure risks.

## Recommendations
Immediate implementation of network segmentation, threat detection systems, and
comprehensive security monitoring capabilities is recommended.
"""
        
        quality = generator._validate_content_quality(sample_content, context)
        print(f"\nQuality Assessment:")
        print(f"- Overall Score: {quality.score:.2f}")
        print(f"- Completeness: {quality.completeness:.2f}")
        print(f"- Professionalism: {quality.professionalism:.2f}")
        print(f"- Accuracy: {quality.accuracy:.2f}")
        
        if quality.issues:
            print(f"- Issues: {', '.join(quality.issues)}")
        if quality.recommendations:
            print(f"- Recommendations: {', '.join(quality.recommendations[:2])}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n")


def demo_specialist_integration():
    """Demonstrate specialist analysis integration"""
    print("=" * 80)
    print("DEMO 3: Specialist Analysis Integration")
    print("=" * 80)
    
    generator = AIEnhancedDeliverableGenerator()
    specialist_results = create_demo_specialist_results()
    
    print("Specialist Analysis Results:")
    print("-" * 40)
    
    for specialist_type, result in specialist_results.items():
        print(f"\n{specialist_type.value.upper()}:")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Key Findings: {len(result.key_findings)} items")
        print(f"  Recommendations: {len(result.recommendations)} items")
        print(f"  Summary: {result.summary[:100]}...")
        
    # Format for AI prompts
    formatted = generator._format_specialist_analysis(specialist_results)
    print(f"\nFormatted for AI Prompts ({len(formatted)} characters):")
    print("-" * 40)
    print(formatted[:800] + "..." if len(formatted) > 800 else formatted)
    
    # Extract recommendations
    recommendations = generator._extract_specialist_recommendations(specialist_results)
    print(f"\nExtracted Recommendations ({len(recommendations)} total):")
    print("-" * 40)
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"{i}. {rec}")
    if len(recommendations) > 5:
        print(f"   ... and {len(recommendations) - 5} more")
    
    print("\n")


def demo_ai_status_and_capabilities():
    """Demonstrate AI status and capability reporting"""
    print("=" * 80)
    print("DEMO 4: AI Status and Capabilities")
    print("=" * 80)
    
    generator = AIEnhancedDeliverableGenerator()
    status = generator.get_ai_status()
    
    print("AI System Status:")
    print("-" * 40)
    print(f"AI Enabled: {status['ai_enabled']}")
    print(f"Model: {status['model']}")
    print(f"Content Types Supported: {len(status['content_types_supported'])}")
    print(f"Quality Thresholds: {len(status['quality_thresholds'])} metrics")
    print(f"Specialist Cache Size: {status['specialist_cache_size']}")
    
    print(f"\nSupported Content Types:")
    for content_type in status['content_types_supported']:
        print(f"- {content_type}")
    
    print(f"\nQuality Thresholds:")
    for metric, threshold in status['quality_thresholds'].items():
        print(f"- {metric}: {threshold}")
    
    # Test quality threshold updates
    print(f"\nUpdating Quality Thresholds...")
    generator.set_quality_thresholds({
        "minimum_score": 0.85,
        "minimum_professionalism": 0.95
    })
    
    updated_status = generator.get_ai_status()
    print(f"Updated Thresholds:")
    for metric, threshold in updated_status['quality_thresholds'].items():
        print(f"- {metric}: {threshold}")
    
    print("\n")


def main():
    """Run all demos"""
    print("AI-Enhanced Deliverable Generator Demo")
    print("=" * 80)
    print("This demo showcases the AI-Enhanced Deliverable Generator capabilities")
    print("including basic generation, AI enhancement, specialist integration,")
    print("and quality validation features.\n")
    
    try:
        demo_basic_generation()
        demo_ai_enhanced_generation()
        demo_specialist_integration()
        demo_ai_status_and_capabilities()
        
        print("=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        print("The AI-Enhanced Deliverable Generator provides:")
        print("✓ Graceful fallback when AI is unavailable")
        print("✓ Integration with specialist agents")  
        print("✓ Content quality validation and improvement")
        print("✓ Professional document generation")
        print("✓ Configurable quality thresholds")
        print("✓ Comprehensive status and capability reporting")
        print("\nReady for Task 2.4: Quality Assurance Framework!")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()