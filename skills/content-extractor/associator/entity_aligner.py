"""Entity alignment using fuzzy matching and semantic similarity."""

import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher


class EntityAligner:
    """Aligns and merges entities from multiple sources."""

    TERM_EQUIVALENCES = {
        "login": ["登录", "登入", "认证", "authenticate"],
        "logout": ["登出", "退出", "signout"],
        "register": ["注册", "登记", "signup"],
        "user": ["用户", "user", "users", "member", "会员"],
        "password": ["密码", "password", "pwd"],
        "order": ["订单", "order", "订购"],
        "payment": ["支付", "payment", "pay", "付款"],
    }

    def __init__(self):
        """Build reverse mapping from Chinese/alt terms to English canonical forms."""
        self._chinese_to_english = {}
        for english, chinese_list in self.TERM_EQUIVALENCES.items():
            for ch in chinese_list:
                self._chinese_to_english[ch] = english

    def normalize(self, text: str) -> str:
        """Normalize text for comparison, translating Chinese terms to English."""
        normalized = text.lower()
        normalized = re.sub(r'[^a-z0-9\u4e00-\u9fff]', '', normalized)

        # Translate Chinese terms to English equivalents
        for chinese, english in self._chinese_to_english.items():
            if chinese in normalized:
                normalized = normalized.replace(chinese, english)

        return normalized

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings (0-1)."""
        norm1 = self.normalize(str1)
        norm2 = self.normalize(str2)

        if norm1 == norm2:
            return 1.0

        for base, equivalents in self.TERM_EQUIVALENCES.items():
            if norm1 in equivalents or norm1 == base:
                if norm2 in equivalents or norm2 == base:
                    return 0.85

        return SequenceMatcher(None, norm1, norm2).ratio()

    def find_similar(
        self,
        target: str,
        entities: List,
        threshold: float = 0.6
    ) -> List[Tuple[Any, float]]:
        """Find entities similar to target."""
        results = []

        for entity in entities:
            entity_name = getattr(entity, 'name', '') or ''
            score = self.calculate_similarity(target, entity_name)
            if score >= threshold:
                results.append((entity, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def find_merge_candidates(
        self,
        entities: List[Dict],
        threshold: float = 0.9
    ) -> List[List[Dict]]:
        """Find groups of entities that should be merged."""
        groups = []
        used = set()

        for i, entity in enumerate(entities):
            if entity['id'] in used:
                continue

            group = [entity]
            used.add(entity['id'])

            for j, other in enumerate(entities[i + 1:], start=i + 1):
                if other['id'] in used:
                    continue

                score = self.calculate_similarity(entity['name'], other['name'])
                if score >= threshold:
                    group.append(other)
                    used.add(other['id'])

            if len(group) > 1:
                groups.append(group)

        return groups

    def suggest_merged_name(self, entities: List[Dict]) -> str:
        """Suggest a merged name from multiple entities."""
        if not entities:
            return ""

        if len(entities) == 1:
            return entities[0]['name']

        for entity in entities:
            if re.search(r'[\u4e00-\u9fff]', entity['name']):
                return entity['name']

        return max(entities, key=lambda x: len(x['name']))['name']
