"""Tests for RefLinker implicit reference resolution."""

import pytest
from associator.ref_linker import RefLinker


class TestRefLinkerPatterns:
    """Test reference pattern extraction."""

    def setup_method(self):
        self.linker = RefLinker()

    def test_explicit_cross_doc_reference(self):
        """Test that explicit patterns still work."""
        text = '详见《配置管理》'
        refs = self.linker.extract_references(text)
        assert len(refs) == 1
        assert refs[0]["type"] == "cross_doc"
        assert "配置管理" in refs[0]["target"]

    def test_explicit_see_reference_with_brackets(self):
        """Test '参见[...]' pattern."""
        text = '参见[RFC 1234]'
        refs = self.linker.extract_references(text)
        assert len(refs) == 1
        assert refs[0]["type"] == "cross_doc"
        assert "RFC 1234" in refs[0]["target"]

    def test_rfc_pattern(self):
        """Test RFC-style references."""
        text = '根据RFC-12规范'
        refs = self.linker.extract_references(text)
        # Both "根据" pattern and RFC pattern match
        assert len(refs) == 2
        rfc_refs = [r for r in refs if "RFC" in r["target"]]
        assert len(rfc_refs) >= 1

    def test_rfc_pattern_without_hyphen(self):
        """Test RFC-style references without hyphen."""
        text = '参照RFC1234标准'
        refs = self.linker.extract_references(text)
        # Both "参照" pattern and RFC pattern match
        assert len(refs) == 2
        rfc_refs = [r for r in refs if "RFC" in r["target"]]
        assert len(rfc_refs) >= 1

    def test_plain_see_reference(self):
        """Test plain '参见X' without brackets."""
        text = '参见配置文档'
        refs = self.linker.extract_references(text)
        assert len(refs) == 1
        assert refs[0]["type"] == "cross_doc"
        assert "配置文档" in refs[0]["target"]

    def test_according_to_pattern(self):
        """Test '依据X' / '按照X' patterns."""
        text = '依据安全策略'
        refs = self.linker.extract_references(text)
        assert len(refs) == 1
        assert "安全策略" in refs[0]["target"]

    def test_conforms_to_pattern(self):
        """Test '符合X' / '满足X' patterns."""
        text = '符合ISO标准'
        refs = self.linker.extract_references(text)
        assert len(refs) == 1
        assert "ISO标准" in refs[0]["target"]


class TestImplicitBackReferences:
    """Test implicit back-reference patterns."""

    def setup_method(self):
        self.linker = RefLinker()

    def test_ru_shang_suo_shu(self):
        """Test '如上所述' back-reference."""
        text = '如上所述'
        refs = self.linker.extract_references(text)
        assert len(refs) == 1
        assert refs[0]["type"] == "implicit"
        assert refs[0]["target"] == "如上所述"

    def test_ru_qian_suo_shu(self):
        """Test '如前所述' back-reference."""
        text = '如前所述'
        refs = self.linker.extract_references(text)
        assert len(refs) == 1
        assert refs[0]["type"] == "implicit"

    def test_qian_shu(self):
        """Test '前述' back-reference."""
        text = '前述方法'
        refs = self.linker.extract_references(text)
        assert len(refs) == 1
        assert refs[0]["type"] == "implicit"

    def test_tong_shang_shu(self):
        """Test '同上述' reference."""
        text = '同上述配置'
        refs = self.linker.extract_references(text)
        assert len(refs) == 1
        assert refs[0]["type"] == "cross_doc"  # Has capture group

    def test_tong_xia_shu(self):
        """Test '同下述' reference."""
        text = '同下述方法'
        refs = self.linker.extract_references(text)
        assert len(refs) == 1
        assert refs[0]["type"] == "cross_doc"

    def test_resolve_back_reference(self):
        """Test resolving '如上所述' to previous function."""
        linker = RefLinker()
        ref = {"type": "implicit", "target": "如上所述", "confidence": 0.7, "match": "如上所述"}
        known_entities = {
            "process_config": ["func_1"],
            "load_data": ["func_2"],
        }
        context = {"previous_entity": "process_config"}
        result, confidence = linker.resolve_implicit_reference(ref, known_entities, context)
        assert result == "func_1"
        assert confidence == 0.85


class TestRFCEreferences:
    """Test RFC reference resolution."""

    def setup_method(self):
        self.linker = RefLinker()

    def test_resolve_rfc_reference(self):
        """Test resolving RFC-12 style references."""
        linker = RefLinker()
        ref = {"type": "cross_doc", "target": "RFC-12", "confidence": 0.95, "match": "RFC-12"}
        known_entities = {
            "process_rfc_12": ["func_rfc12"],
            "other_func": ["func_other"],
        }
        result, confidence = linker.resolve_implicit_reference(ref, known_entities)
        assert result == "func_rfc12"
        assert confidence == 0.9

    def test_resolve_rfc_without_hyphen(self):
        """Test resolving RFC12 style references."""
        linker = RefLinker()
        ref = {"type": "cross_doc", "target": "RFC123", "confidence": 0.95, "match": "RFC123"}
        known_entities = {
            "RFC 123 implementation": ["func_rfc123"],
        }
        result, confidence = linker.resolve_implicit_reference(ref, known_entities)
        assert result == "func_rfc123"


class TestSameConfigReferences:
    """Test '同配置' style references."""

    def setup_method(self):
        self.linker = RefLinker()

    def test_tong_config_reference(self):
        """Test '同配置' type references resolve correctly."""
        linker = RefLinker()
        ref = {"type": "cross_doc", "target": "同配置", "confidence": 0.95, "match": "同配置"}
        known_entities = {
            "配置管理": ["func_config"],
            "数据加载": ["func_load"],
        }
        result, confidence = linker.resolve_implicit_reference(ref, known_entities)
        assert result == "func_config"

    def test_tong_document_reference(self):
        """Test '同文档' type references resolve correctly."""
        linker = RefLinker()
        ref = {"type": "cross_doc", "target": "同文档", "confidence": 0.95, "match": "同文档"}
        known_entities = {
            "文档处理": ["func_doc"],
        }
        result, confidence = linker.resolve_implicit_reference(ref, known_entities)
        assert result == "func_doc"


class TestSequentialReferences:
    """Test sequential reference patterns."""

    def setup_method(self):
        self.linker = RefLinker()

    def test_zhi_hou_pattern(self):
        """Test '之后' pattern."""
        text = '处理完成后，之后执行'
        refs = self.linker.extract_references(text)
        seq_refs = [r for r in refs if r["type"] == "sequential"]
        assert len(seq_refs) == 1
        assert seq_refs[0]["target"] == "implicit_next"

    def test_sui_hou_pattern(self):
        """Test '随后' pattern."""
        text = '初始化随后进行'
        refs = self.linker.extract_references(text)
        seq_refs = [r for r in refs if r["type"] == "sequential"]
        assert len(seq_refs) == 1

    def test_jie_xia_lai_pattern(self):
        """Test '接下来' pattern."""
        text = '验证接下来测试'
        refs = self.linker.extract_references(text)
        seq_refs = [r for r in refs if r["type"] == "sequential"]
        assert len(seq_refs) == 1

    def test_resolve_sequential_reference(self):
        """Test resolving sequential reference to next entity."""
        linker = RefLinker()
        ref = {"type": "sequential", "target": "implicit_next", "confidence": 0.6, "match": "之后"}
        known_entities = {
            "step_one": ["func_1"],
            "step_two": ["func_2"],
        }
        context = {"next_entity": "step_two"}
        result, confidence = linker.resolve_implicit_reference(ref, known_entities, context)
        assert result == "func_2"
        assert confidence == 0.8


class TestExistingFunctionality:
    """Test that existing patterns still work."""

    def setup_method(self):
        self.linker = RefLinker()

    def test_section_reference(self):
        """Test section reference pattern."""
        text = '见第3.2节'
        refs = self.linker.extract_references(text)
        section_refs = [r for r in refs if r["type"] == "section"]
        assert len(section_refs) == 1
        assert section_refs[0]["target"] == "section_3.2"

    def test_figure_reference(self):
        """Test figure reference pattern."""
        text = '如图5'
        refs = self.linker.extract_references(text)
        section_refs = [r for r in refs if r["type"] == "section"]
        assert len(section_refs) == 1
        assert section_refs[0]["target"] == "section_5"

    def test_url_reference(self):
        """Test URL reference pattern."""
        text = '访问https://example.com/docs'
        refs = self.linker.extract_references(text)
        url_refs = [r for r in refs if r["type"] == "url"]
        assert len(url_refs) == 1
        assert "https://example.com/docs" in url_refs[0]["target"]

    def test_resolve_existing_reference(self):
        """Test that resolve_reference still works."""
        linker = RefLinker()
        ref = {"type": "cross_doc", "target": "配置管理", "confidence": 0.95, "match": "配置管理"}
        known_entities = {"配置管理": ["func_config"]}
        result = linker.resolve_reference(ref, known_entities)
        assert result == "func_config"


class TestConfidenceScoring:
    """Test confidence scoring in resolution."""

    def setup_method(self):
        self.linker = RefLinker()

    def test_back_reference_confidence_with_context(self):
        """Test back-reference confidence when context is provided."""
        linker = RefLinker()
        ref = {"type": "implicit", "target": "如上所述", "confidence": 0.7}
        known_entities = {"func_a": ["id_a"]}
        context = {"previous_entity": "func_a"}
        _, confidence = linker.resolve_implicit_reference(ref, known_entities, context)
        assert confidence == 0.85

    def test_back_reference_confidence_without_context(self):
        """Test back-reference confidence when no context is provided."""
        linker = RefLinker()
        ref = {"type": "implicit", "target": "如上所述", "confidence": 0.7}
        known_entities = {"func_a": ["id_a"]}
        _, confidence = linker.resolve_implicit_reference(ref, known_entities)
        assert confidence == 0.6
