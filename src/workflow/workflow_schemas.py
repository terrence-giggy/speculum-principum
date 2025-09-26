"""
Workflow Schema Validation Module
Defines and validates the schema for workflow YAML files
"""

import jsonschema
from typing import Dict, List, Any, Tuple
import logging
import re

logger = logging.getLogger(__name__)


class WorkflowSchemaValidator:
    """
    Validates workflow YAML files against the expected schema.
    
    This class provides comprehensive validation for workflow definitions,
    ensuring they contain all required fields and conform to expected types
    and constraints.
    """
    
    # JSON Schema for workflow validation
    WORKFLOW_SCHEMA = {
        "type": "object",
        "required": ["name", "trigger_labels", "deliverables"],
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,
                "description": "Human-readable name for the workflow"
            },
            "description": {
                "type": "string",
                "description": "Brief description of the workflow purpose"
            },
            "version": {
                "type": "string",
                "pattern": r"^\d+\.\d+\.\d+$",
                "description": "Semantic version string (e.g., '1.0.0')"
            },
            "trigger_labels": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "string",
                    "minLength": 1,
                    "pattern": r"^[a-zA-Z0-9-_]+$"
                },
                "description": "Labels that trigger this workflow (in addition to 'site-monitor')"
            },
            "deliverables": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["name", "title", "description"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "minLength": 1,
                            "pattern": r"^[a-zA-Z0-9-_]+$",
                            "description": "Unique identifier for the deliverable"
                        },
                        "title": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Human-readable title for the deliverable"
                        },
                        "description": {
                            "type": "string",
                            "minLength": 1,
                            "description": "Description of what this deliverable contains"
                        },
                        "template": {
                            "type": "string",
                            "description": "Template file to use for this deliverable"
                        },
                        "required": {
                            "type": "boolean",
                            "description": "Whether this deliverable is required"
                        },
                        "order": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Order in which this deliverable should be generated"
                        }
                    },
                    "additionalProperties": False
                },
                "description": "List of deliverables to generate"
            },
            "processing": {
                "type": "object",
                "properties": {
                    "timeout": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Processing timeout in seconds"
                    },
                    "max_retries": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Maximum number of retry attempts"
                    }
                },
                "additionalProperties": False,
                "description": "Processing configuration options"
            },
            "validation": {
                "type": "object",
                "properties": {
                    "required_sections": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Required sections in generated content"
                    },
                    "min_length": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Minimum content length"
                    },
                    "min_word_count": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Minimum word count for generated content"
                    }
                },
                "additionalProperties": False,
                "description": "Validation rules for generated content"
            },
            "output": {
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "html", "text"],
                        "description": "Output format for deliverables"
                    },
                    "directory": {
                        "type": "string",
                        "description": "Output directory for generated files"
                    },
                    "folder_structure": {
                        "type": "string",
                        "description": "Folder structure pattern for output files"
                    }
                },
                "additionalProperties": False,
                "description": "Output configuration options"
            }
        },
        "additionalProperties": False
    }
    
    @classmethod
    def validate_workflow(cls, workflow_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate workflow data against the schema.
        
        Args:
            workflow_data: Dictionary containing workflow configuration
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        try:
            jsonschema.validate(instance=workflow_data, schema=cls.WORKFLOW_SCHEMA)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
            if e.path:
                errors.append(f"  at path: {' -> '.join(str(p) for p in e.path)}")
        except jsonschema.SchemaError as e:
            errors.append(f"Schema definition error: {e.message}")
        
        # Additional custom validations
        if not errors:
            custom_errors = cls._perform_custom_validations(workflow_data)
            errors.extend(custom_errors)
        
        return len(errors) == 0, errors
    
    @classmethod
    def _perform_custom_validations(cls, workflow_data: Dict[str, Any]) -> List[str]:
        """
        Perform custom validations beyond basic schema validation.
        
        Args:
            workflow_data: Dictionary containing workflow configuration
            
        Returns:
            List of error messages
        """
        errors = []
        
        # Check for duplicate deliverable names
        deliverables = workflow_data.get('deliverables', [])
        deliverable_names = [d.get('name') for d in deliverables if d.get('name')]
        duplicate_names = set([name for name in deliverable_names if deliverable_names.count(name) > 1])
        
        if duplicate_names:
            errors.append(f"Duplicate deliverable names found: {', '.join(duplicate_names)}")
        
        # Check for duplicate deliverable orders
        deliverable_orders = [d.get('order') for d in deliverables if d.get('order') is not None]
        duplicate_orders = set([order for order in deliverable_orders if deliverable_orders.count(order) > 1])
        
        if duplicate_orders:
            errors.append(f"Duplicate deliverable orders found: {', '.join(map(str, duplicate_orders))}")
        
        # Validate trigger labels don't include 'site-monitor' (it's automatic)
        trigger_labels = workflow_data.get('trigger_labels', [])
        if 'site-monitor' in trigger_labels:
            errors.append("trigger_labels should not include 'site-monitor' as it's automatically required")
        
        return errors
    
    @classmethod
    def validate_deliverable_names(cls, deliverables: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validate that deliverable names are unique and properly formatted.
        
        Args:
            deliverables: List of deliverable dictionaries
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        names = []
        
        for i, deliverable in enumerate(deliverables):
            name = deliverable.get('name')
            if not name:
                errors.append(f"Deliverable {i+1} missing required 'name' field")
                continue
            
            if not isinstance(name, str):
                errors.append(f"Deliverable {i+1} name must be a string, got {type(name).__name__}")
                continue
            
            if name in names:
                errors.append(f"Duplicate deliverable name: '{name}'")
            else:
                names.append(name)
            
            # Validate name format
            if not re.match(r'^[a-zA-Z0-9-_]+$', name):
                msg = (f"Deliverable name '{name}' contains invalid characters. "
                      "Use only letters, numbers, hyphens, and underscores.")
                errors.append(msg)
        
        return len(errors) == 0, errors