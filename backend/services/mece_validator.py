"""
MECE Validator - Post-generation validation and cleanup for topic trees
"""
from typing import List, Dict, Tuple, Set
from collections import defaultdict
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Topic
from core.logging_config import logger

validator_logger = logger.getChild("mece_validator")

class MECEValidator:
    """
    Validates and cleans topic hierarchies to ensure MECE compliance
    """
    
    def __init__(self):
        self.stop_words = {'of', 'and', 'the', 'in', 'for', 'with', 'to', 'a', 'an', 'on', 'at', 'by'}
        
    async def validate_and_clean_subtopics(
        self, 
        subtopics: List[Dict], 
        parent_topic: Topic,
        auto_fix: bool = True
    ) -> Tuple[List[Dict], List[str]]:
        """
        Validate subtopics for MECE compliance and optionally fix issues
        Returns: (cleaned_subtopics, violations_found)
        """
        violations = []
        cleaned_subtopics = subtopics.copy()
        
        # 1. Remove exact duplicates
        cleaned_subtopics, duplicate_violations = self._remove_duplicates(cleaned_subtopics)
        violations.extend(duplicate_violations)
        
        # 2. Detect and handle subset relationships
        if auto_fix:
            cleaned_subtopics, subset_violations = self._fix_subset_relationships(cleaned_subtopics)
            violations.extend(subset_violations)
        else:
            subset_violations = self._detect_subset_relationships(cleaned_subtopics)
            violations.extend(subset_violations)
        
        # 3. Detect high overlap
        overlap_violations = self._detect_high_overlap(cleaned_subtopics)
        violations.extend(overlap_violations)
        
        # 4. Check for generic + specific pattern
        pattern_violations = self._detect_generic_specific_pattern(cleaned_subtopics)
        violations.extend(pattern_violations)
        
        # 5. Ensure minimum coverage
        if len(cleaned_subtopics) < 2:
            violations.append("Insufficient subtopics for comprehensive coverage")
        
        # 6. Check abstraction consistency
        abstraction_violations = self._check_abstraction_consistency(cleaned_subtopics)
        violations.extend(abstraction_violations)
        
        return cleaned_subtopics, violations
    
    def _remove_duplicates(self, subtopics: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """Remove exact duplicate names"""
        seen_names = {}
        cleaned = []
        violations = []
        
        for subtopic in subtopics:
            name_lower = subtopic['name'].lower()
            if name_lower in seen_names:
                violations.append(f"Duplicate removed: '{subtopic['name']}'")
            else:
                seen_names[name_lower] = True
                cleaned.append(subtopic)
        
        return cleaned, violations
    
    def _fix_subset_relationships(self, subtopics: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """Fix subset relationships by merging or renaming"""
        cleaned = []
        violations = []
        skip_indices = set()
        
        for i, sub1 in enumerate(subtopics):
            if i in skip_indices:
                continue
                
            merged = False
            name1 = sub1['name'].lower()
            
            for j, sub2 in enumerate(subtopics[i+1:], i+1):
                if j in skip_indices:
                    continue
                    
                name2 = sub2['name'].lower()
                
                # Check if one contains the other
                if name1 in name2:
                    # sub1 is more general, keep it
                    violations.append(f"Subset relationship fixed: kept '{sub1['name']}', removed '{sub2['name']}'")
                    skip_indices.add(j)
                elif name2 in name1:
                    # sub2 is more general, keep it
                    violations.append(f"Subset relationship fixed: kept '{sub2['name']}', removed '{sub1['name']}'")
                    skip_indices.add(i)
                    merged = True
                    break
            
            if not merged:
                cleaned.append(sub1)
        
        # Add remaining non-skipped items
        for i, sub in enumerate(subtopics):
            if i not in skip_indices and sub not in cleaned:
                cleaned.append(sub)
        
        return cleaned, violations
    
    def _detect_subset_relationships(self, subtopics: List[Dict]) -> List[str]:
        """Detect but don't fix subset relationships"""
        violations = []
        
        for i, sub1 in enumerate(subtopics):
            name1 = sub1['name'].lower()
            
            for j, sub2 in enumerate(subtopics[i+1:], i+1):
                name2 = sub2['name'].lower()
                
                if name1 in name2 or name2 in name1:
                    violations.append(f"Subset relationship: '{sub1['name']}' and '{sub2['name']}'")
        
        return violations
    
    def _detect_high_overlap(self, subtopics: List[Dict]) -> List[str]:
        """Detect topics with high word overlap"""
        violations = []
        
        for i, sub1 in enumerate(subtopics):
            words1 = set(sub1['name'].lower().split()) - self.stop_words
            
            for j, sub2 in enumerate(subtopics[i+1:], i+1):
                words2 = set(sub2['name'].lower().split()) - self.stop_words
                
                if words1 and words2:
                    overlap = len(words1 & words2)
                    min_len = min(len(words1), len(words2))
                    
                    if min_len > 0 and overlap / min_len > 0.6:
                        violations.append(
                            f"High overlap ({overlap}/{min_len} words): "
                            f"'{sub1['name']}' and '{sub2['name']}'"
                        )
        
        return violations
    
    def _detect_generic_specific_pattern(self, subtopics: List[Dict]) -> List[str]:
        """Detect problematic generic + specific patterns"""
        violations = []
        generic_patterns = [
            'applications', 'techniques', 'methods', 'approaches', 
            'systems', 'models', 'algorithms', 'concepts'
        ]
        
        for pattern in generic_patterns:
            # Find all topics containing this pattern
            matching_topics = [
                (i, sub) for i, sub in enumerate(subtopics) 
                if pattern in sub['name'].lower()
            ]
            
            if len(matching_topics) > 1:
                # Check if we have both generic and specific versions
                generic_exists = any(
                    len(sub['name'].split()) <= 2 
                    for _, sub in matching_topics
                )
                specific_exists = any(
                    len(sub['name'].split()) > 3 
                    for _, sub in matching_topics
                )
                
                if generic_exists and specific_exists:
                    topic_names = [sub['name'] for _, sub in matching_topics]
                    violations.append(
                        f"Generic + specific pattern for '{pattern}': {topic_names}"
                    )
        
        return violations
    
    def _check_abstraction_consistency(self, subtopics: List[Dict]) -> List[str]:
        """Check if all siblings have consistent abstraction levels"""
        violations = []
        
        # Calculate abstraction score based on name length and specificity
        abstraction_scores = []
        for sub in subtopics:
            name = sub['name']
            words = name.lower().split()
            
            # Factors that indicate more specific/concrete topics
            specificity_score = 0
            specificity_score += len(words) * 0.3  # Longer names are more specific
            specificity_score += sum(1 for w in words if w.endswith('ing')) * 0.5  # Gerunds
            specificity_score += sum(1 for w in words if w.endswith('tion')) * 0.3  # Nominalizations
            specificity_score += sum(1 for w in words if any(c.isdigit() for c in w)) * 1.0  # Numbers
            
            abstraction_scores.append((name, specificity_score))
        
        # Check for large variance in abstraction
        if abstraction_scores:
            scores_only = [score for _, score in abstraction_scores]
            avg_score = sum(scores_only) / len(scores_only)
            
            for name, score in abstraction_scores:
                if abs(score - avg_score) > avg_score * 0.7:  # >70% deviation
                    level = "too specific" if score > avg_score else "too general"
                    violations.append(f"Inconsistent abstraction: '{name}' is {level}")
        
        return violations
    
    async def validate_entire_tree(
        self, 
        db: AsyncSession, 
        root_topic_id: int = None
    ) -> Dict[str, List[str]]:
        """
        Validate the entire topic tree for MECE violations
        Returns dictionary of parent_id -> violations
        """
        all_violations = {}
        
        # Get all topics
        query = select(Topic)
        if root_topic_id:
            # Get all descendants of root
            query = query.where(Topic.id == root_topic_id)
        
        result = await db.execute(query)
        topics = result.scalars().all()
        
        # Build parent-children map
        parent_children = defaultdict(list)
        topic_map = {}
        
        for topic in topics:
            topic_map[topic.id] = topic
            if topic.parent_id:
                parent_children[topic.parent_id].append(topic)
        
        # Validate each parent's children
        for parent_id, children in parent_children.items():
            if len(children) < 2:
                continue
            
            # Convert to dict format for validation
            children_dicts = [
                {
                    'name': child.name,
                    'description': child.description,
                    'difficulty_min': child.difficulty_min,
                    'difficulty_max': child.difficulty_max
                }
                for child in children
            ]
            
            parent = topic_map.get(parent_id)
            if parent:
                _, violations = await self.validate_and_clean_subtopics(
                    children_dicts, 
                    parent, 
                    auto_fix=False
                )
                
                if violations:
                    all_violations[parent.name] = violations
        
        return all_violations

# Global instance
mece_validator = MECEValidator()