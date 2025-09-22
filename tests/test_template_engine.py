"""
Tests for the TemplateEngine module.

This test suite provides comprehensive coverage of the template engine functionality
including template loading, rendering, variable substitution, conditionals, loops,
sections, template inheritance, and error handling.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock

from src.template_engine import TemplateEngine, TemplateMetadata


class TestTemplateEngine:
    """Test suite for the TemplateEngine class."""
    
    def setup_method(self):
        """Set up test environment before each test."""
        # Create temporary directory for templates
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.temp_dir)
        self.engine = TemplateEngine(self.templates_dir)
    
    def teardown_method(self):
        """Clean up test environment after each test."""
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_template_engine_initialization(self):
        """Test template engine initialization."""
        engine = TemplateEngine()
        assert engine.templates_dir == Path("templates")
        assert isinstance(engine.template_cache, dict)
        assert isinstance(engine.metadata_cache, dict)
        
        # Test with custom directory (using a valid temp path)
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_engine = TemplateEngine(temp_dir)
            assert custom_engine.templates_dir == Path(temp_dir)
    
    def test_create_templates_directory(self):
        """Test that template engine creates templates directory if it doesn't exist."""
        new_dir = Path(self.temp_dir) / "new_templates"
        assert not new_dir.exists()
        
        engine = TemplateEngine(new_dir)
        assert new_dir.exists()
        assert new_dir.is_dir()
    
    def test_load_simple_template(self):
        """Test loading a simple template without front matter."""
        template_content = "# Hello {{ name }}\n\nThis is a simple template."
        template_file = self.templates_dir / "simple.md"
        template_file.write_text(template_content)
        
        content = self.engine.load_template("simple")
        assert content == template_content
        
        # Check that template is cached
        assert "simple" in self.engine.template_cache
        assert self.engine.template_cache["simple"] == template_content
    
    def test_load_template_with_front_matter(self):
        """Test loading a template with YAML front matter."""
        template_content = """---
name: "Test Template"
description: "A template for testing"
type: "document"
variables:
  name: "User name"
  title: "Document title"
---

# {{ title }}

Hello {{ name }}!"""
        
        template_file = self.templates_dir / "front_matter.md"
        template_file.write_text(template_content)
        
        content = self.engine.load_template("front_matter")
        expected_content = "\n# {{ title }}\n\nHello {{ name }}!"
        assert content == expected_content
        
        # Check metadata
        metadata = self.engine.metadata_cache["front_matter"]
        assert metadata.name == "Test Template"
        assert metadata.description == "A template for testing"
        assert metadata.type == "document"
        assert metadata.variables == {"name": "User name", "title": "Document title"}
    
    def test_template_not_found(self):
        """Test behavior when template file doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Template not found: nonexistent"):
            self.engine.load_template("nonexistent")
    
    def test_invalid_yaml_front_matter(self):
        """Test handling of invalid YAML front matter."""
        template_content = """---
invalid: yaml: content: [
---

# Template content"""
        
        template_file = self.templates_dir / "invalid_yaml.md"
        template_file.write_text(template_content)
        
        # Should fall back to default metadata
        content = self.engine.load_template("invalid_yaml")
        assert "# Template content" in content
        
        metadata = self.engine.metadata_cache["invalid_yaml"]
        assert metadata.name == "Unknown"
    
    def test_simple_variable_substitution(self):
        """Test basic variable substitution."""
        template_content = "Hello {{ name }}! Today is {{ date }}."
        template_file = self.templates_dir / "variables.md"
        template_file.write_text(template_content)
        
        context = {"name": "World", "date": "2023-01-01"}
        result = self.engine.render_template("variables", context)
        
        assert result == "Hello World! Today is 2023-01-01."
    
    def test_dot_notation_variables(self):
        """Test variable access using dot notation."""
        template_content = "User: {{ user.name }}, Email: {{ user.email }}"
        template_file = self.templates_dir / "dot_notation.md"
        template_file.write_text(template_content)
        
        context = {
            "user": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }
        result = self.engine.render_template("dot_notation", context)
        
        assert result == "User: John Doe, Email: john@example.com"
    
    def test_undefined_variables(self):
        """Test handling of undefined variables."""
        template_content = "Hello {{ undefined_var }}!"
        template_file = self.templates_dir / "undefined.md"
        template_file.write_text(template_content)
        
        context = {}
        result = self.engine.render_template("undefined", context)
        
        assert result == "Hello !"
    
    def test_conditional_rendering_true(self):
        """Test conditional rendering when condition is true."""
        template_content = """{% if show_greeting %}
Hello {{ name }}!
{% endif %}"""
        template_file = self.templates_dir / "conditional.md"
        template_file.write_text(template_content)
        
        context = {"show_greeting": True, "name": "World"}
        result = self.engine.render_template("conditional", context)
        
        assert "Hello World!" in result
    
    def test_conditional_rendering_false(self):
        """Test conditional rendering when condition is false."""
        template_content = """{% if show_greeting %}
Hello {{ name }}!
{% endif %}"""
        template_file = self.templates_dir / "conditional_false.md"
        template_file.write_text(template_content)
        
        context = {"show_greeting": False, "name": "World"}
        result = self.engine.render_template("conditional_false", context)
        
        assert "Hello World!" not in result
    
    def test_conditional_not_operator(self):
        """Test conditional rendering with 'not' operator."""
        template_content = """{% if not hide_content %}
This content is visible.
{% endif %}"""
        template_file = self.templates_dir / "conditional_not.md"
        template_file.write_text(template_content)
        
        context = {"hide_content": False}
        result = self.engine.render_template("conditional_not", context)
        
        assert "This content is visible." in result
    
    def test_conditional_equality(self):
        """Test conditional rendering with equality comparison."""
        template_content = """{% if status == "active" %}
Status is active!
{% endif %}"""
        template_file = self.templates_dir / "conditional_eq.md"
        template_file.write_text(template_content)
        
        context = {"status": "active"}
        result = self.engine.render_template("conditional_eq", context)
        
        assert "Status is active!" in result
    
    def test_conditional_inequality(self):
        """Test conditional rendering with inequality comparison."""
        template_content = """{% if status != "inactive" %}
Status is not inactive!
{% endif %}"""
        template_file = self.templates_dir / "conditional_neq.md"
        template_file.write_text(template_content)
        
        context = {"status": "active"}
        result = self.engine.render_template("conditional_neq", context)
        
        assert "Status is not inactive!" in result
    
    def test_loop_rendering(self):
        """Test loop rendering with list iteration."""
        template_content = """{% for item in items %}
- {{ item }}
{% endfor %}"""
        template_file = self.templates_dir / "loop.md"
        template_file.write_text(template_content)
        
        context = {"items": ["apple", "banana", "cherry"]}
        result = self.engine.render_template("loop", context)
        
        assert "- apple" in result
        assert "- banana" in result  
        assert "- cherry" in result
    
    def test_loop_variables(self):
        """Test loop variables (index, first, last, etc.)."""
        template_content = """{% for item in items %}
{{ loop.index }}: {{ item }} ({% if loop.first %}first{% endif %}{% if loop.last %}last{% endif %})
{% endfor %}"""
        template_file = self.templates_dir / "loop_vars.md"
        template_file.write_text(template_content)
        
        context = {"items": ["A", "B"]}
        result = self.engine.render_template("loop_vars", context)
        
        assert "1: A (first)" in result
        assert "2: B (last)" in result
    
    def test_section_rendering(self):
        """Test section rendering."""
        template_content = """{% section header %}
# Default Header
{% endsection %}

{% section content %}
Default content here.
{% endsection %}"""
        template_file = self.templates_dir / "sections.md"
        template_file.write_text(template_content)
        
        sections = {
            "header": "# Custom Header"
        }
        result = self.engine.render_template("sections", {}, sections)
        
        assert "# Custom Header" in result
        assert "Default content here." in result
        assert "# Default Header" not in result
    
    def test_include_directive(self):
        """Test include directive for template composition."""
        # Create included template
        included_content = "This is included content with {{ variable }}."
        included_file = self.templates_dir / "included.md"
        included_file.write_text(included_content)
        
        # Create main template
        main_content = """Main template start.
{% include "included" %}
Main template end."""
        main_file = self.templates_dir / "main.md"
        main_file.write_text(main_content)
        
        context = {"variable": "test value"}
        result = self.engine.render_template("main", context)
        
        assert "Main template start." in result
        assert "This is included content with test value." in result
        assert "Main template end." in result
    
    def test_template_inheritance(self):
        """Test template inheritance."""
        # Create parent template
        parent_content = """---
name: "Parent Template"
---

{% section header %}
# Default Header
{% endsection %}

{% section content %}
Default parent content.
{% endsection %}"""
        parent_file = self.templates_dir / "parent.md"
        parent_file.write_text(parent_content)
        
        # Create child template
        child_content = """---
name: "Child Template"
extends: "parent"
---

{% section header %}
# Child Header Override
{% endsection %}"""
        child_file = self.templates_dir / "child.md"
        child_file.write_text(child_content)
        
        result = self.engine.render_template("child", {})
        
        assert "# Child Header Override" in result
        assert "Default parent content." in result
        assert "# Default Header" not in result
    
    def test_system_variables(self):
        """Test that system variables are available in templates."""
        template_content = "Date: {{ date }}, Time: {{ time }}"
        template_file = self.templates_dir / "system_vars.md"
        template_file.write_text(template_content)
        
        result = self.engine.render_template("system_vars", {})
        
        assert "Date: " in result
        assert "Time: " in result
        # Check that actual date/time values are present
        current_date = datetime.now().strftime('%Y-%m-%d')
        assert current_date in result
    
    def test_list_templates(self):
        """Test listing available templates."""
        # Create multiple templates
        template1 = self.templates_dir / "template1.md"
        template1.write_text("Template 1")
        
        subdir = self.templates_dir / "subdir"
        subdir.mkdir()
        template2 = subdir / "template2.md"
        template2.write_text("Template 2")
        
        templates = self.engine.list_templates()
        
        assert "template1" in templates
        assert "subdir/template2" in templates
        assert len(templates) == 2
    
    def test_get_template_metadata(self):
        """Test retrieving template metadata."""
        template_content = """---
name: "Test Template"
description: "A test template"
version: "2.0"
---

Template content"""
        template_file = self.templates_dir / "metadata_test.md"
        template_file.write_text(template_content)
        
        metadata = self.engine.get_template_metadata("metadata_test")
        
        assert metadata.name == "Test Template"
        assert metadata.description == "A test template"
        assert metadata.version == "2.0"
    
    def test_validate_template_syntax(self):
        """Test template syntax validation."""
        # Valid template
        valid_content = """{% if condition %}
{{ variable }}
{% endif %}"""
        valid_file = self.templates_dir / "valid.md"
        valid_file.write_text(valid_content)
        
        result = self.engine.validate_template("valid")
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        
        # Invalid template with unmatched braces
        invalid_content = "{{ unclosed_variable"
        invalid_file = self.templates_dir / "invalid.md"
        invalid_file.write_text(invalid_content)
        
        result = self.engine.validate_template("invalid")
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    def test_template_caching(self):
        """Test that templates are properly cached."""
        template_content = "Cached template"
        template_file = self.templates_dir / "cached.md"
        template_file.write_text(template_content)
        
        # Load template
        content1 = self.engine.load_template("cached")
        assert "cached" in self.engine.template_cache
        
        # Modify file
        template_file.write_text("Modified template")
        
        # Load again (should return cached version)
        content2 = self.engine.load_template("cached")
        assert content1 == content2
        assert content2 == "Cached template"
        
        # Force reload
        content3 = self.engine.load_template("cached", force_reload=True)
        assert content3 == "Modified template"
    
    def test_error_handling_missing_include(self):
        """Test error handling for missing include files."""
        template_content = '{% include "nonexistent" %}'
        template_file = self.templates_dir / "missing_include.md"
        template_file.write_text(template_content)
        
        result = self.engine.render_template("missing_include", {})
        
        # Should include error comment
        assert "Failed to include: nonexistent" in result
    
    def test_literal_value_parsing(self):
        """Test parsing of literal values in conditions."""
        template_content = '''{% if name == "test" %}
String match!
{% endif %}
{% if count == 42 %}
Number match!
{% endif %}
{% if active == true %}
Boolean match!
{% endif %}'''
        template_file = self.templates_dir / "literals.md"
        template_file.write_text(template_content)
        
        context = {"name": "test", "count": 42, "active": True}
        result = self.engine.render_template("literals", context)
        
        assert "String match!" in result
        assert "Number match!" in result  
        assert "Boolean match!" in result
    
    def test_complex_nested_rendering(self):
        """Test complex nested template features."""
        template_content = '''{% for section in sections %}
## {{ section.title }}

{% if section.items %}
{% for item in section.items %}
- {{ item.name }}: {{ item.value }}
{% endfor %}
{% endif %}

{% endfor %}'''
        template_file = self.templates_dir / "complex.md"
        template_file.write_text(template_content)
        
        context = {
            "sections": [
                {
                    "title": "Section 1",
                    "items": [
                        {"name": "Item A", "value": "Value A"},
                        {"name": "Item B", "value": "Value B"}
                    ]
                },
                {
                    "title": "Section 2", 
                    "items": []
                }
            ]
        }
        
        result = self.engine.render_template("complex", context)
        
        assert "## Section 1" in result
        assert "## Section 2" in result
        assert "- Item A: Value A" in result
        assert "- Item B: Value B" in result


class TestTemplateMetadata:
    """Test suite for the TemplateMetadata class."""
    
    def test_template_metadata_creation(self):
        """Test creation of TemplateMetadata objects."""
        metadata = TemplateMetadata(
            name="Test Template",
            description="A test template",
            type="document"
        )
        
        assert metadata.name == "Test Template"
        assert metadata.description == "A test template"
        assert metadata.type == "document"
        assert metadata.variables == {}
        assert metadata.sections == []
        assert metadata.version == "1.0"
        assert metadata.author == "System"
    
    def test_template_metadata_with_all_fields(self):
        """Test TemplateMetadata with all fields specified."""
        metadata = TemplateMetadata(
            name="Full Template",
            description="Complete template",
            type="document",
            extends="base",
            variables={"var1": "description1"},
            sections=["section1", "section2"],
            version="2.0",
            author="Test Author"
        )
        
        assert metadata.name == "Full Template"
        assert metadata.extends == "base"
        assert metadata.variables == {"var1": "description1"}
        assert metadata.sections == ["section1", "section2"]
        assert metadata.version == "2.0"
        assert metadata.author == "Test Author"


class TestTemplateEngineEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.templates_dir = Path(self.temp_dir)
        self.engine = TemplateEngine(self.templates_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_empty_template(self):
        """Test rendering of empty template."""
        template_file = self.templates_dir / "empty.md"
        template_file.write_text("")
        
        result = self.engine.render_template("empty", {})
        assert result == ""
    
    def test_template_with_only_front_matter(self):
        """Test template with only front matter and no content."""
        template_content = """---
name: "Only Front Matter"
---"""
        template_file = self.templates_dir / "only_front_matter.md"
        template_file.write_text(template_content)
        
        result = self.engine.render_template("only_front_matter", {})
        assert result == ""
    
    def test_circular_includes(self):
        """Test handling of circular includes."""
        # Template A includes B
        template_a = '{% include "template_b" %}'
        file_a = self.templates_dir / "template_a.md"
        file_a.write_text(template_a)
        
        # Template B includes A (circular)
        template_b = '{% include "template_a" %}'
        file_b = self.templates_dir / "template_b.md"
        file_b.write_text(template_b)
        
        # Should handle gracefully (likely with recursion limit)
        result = self.engine.render_template("template_a", {})
        # The exact behavior depends on implementation,
        # but it shouldn't crash
        assert isinstance(result, str)
    
    def test_malformed_template_syntax(self):
        """Test handling of malformed template syntax."""
        malformed_content = """
{% if condition
{{ unclosed_variable
{% for item in items
Content here
{% endif %}
"""
        template_file = self.templates_dir / "malformed.md"
        template_file.write_text(malformed_content)
        
        validation = self.engine.validate_template("malformed")
        assert not validation["valid"]
        assert len(validation["errors"]) > 0
    
    def test_very_large_template(self):
        """Test handling of very large templates."""
        # Create a large template with many variables
        large_content = "\n".join([f"Line {i}: {{{{ var{i} }}}}" for i in range(1000)])
        template_file = self.templates_dir / "large.md"
        template_file.write_text(large_content)
        
        # Create context with corresponding variables
        context = {f"var{i}": f"value{i}" for i in range(1000)}
        
        result = self.engine.render_template("large", context)
        
        # Check that substitution worked
        assert "Line 0: value0" in result
        assert "Line 999: value999" in result
    
    @patch('builtins.open', side_effect=PermissionError("Access denied"))
    def test_permission_error_handling(self, mock_open):
        """Test handling of file permission errors."""
        # Create a file first so it can be found
        template_file = self.templates_dir / "permission_test.md"
        template_file.write_text("test content")
        
        # Now mock the open to fail
        with pytest.raises(ValueError, match="Failed to load template"):
            self.engine.load_template("permission_test")
    
    def test_unicode_content(self):
        """Test handling of Unicode content in templates."""
        unicode_content = "Hello {{ name }}! 🌟 Español: {{ mensaje }}"
        template_file = self.templates_dir / "unicode.md"
        template_file.write_text(unicode_content, encoding='utf-8')
        
        context = {"name": "世界", "mensaje": "¡Hola!"}
        result = self.engine.render_template("unicode", context)
        
        assert "Hello 世界!" in result
        assert "🌟" in result
        assert "¡Hola!" in result