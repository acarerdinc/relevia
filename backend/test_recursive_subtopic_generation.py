#!/usr/bin/env python3
"""
Test script to recursively generate subtopics and validate MECE principles
This will generate at least 1000 subtopics and analyze the tree structure
"""
import asyncio
import json
import time
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter
from sqlalchemy import select, func
from db.database import AsyncSessionLocal
from db.models import Topic, UserSkillProgress
from services.dynamic_topic_generator import DynamicTopicGenerator
from services.dynamic_ontology_service import DynamicOntologyService
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime


class RecursiveSubtopicGenerator:
    def __init__(self):
        self.topic_generator = DynamicTopicGenerator()
        self.ontology_service = DynamicOntologyService()
        self.generated_count = 0
        self.target_count = 1000
        self.tree_data = {}
        self.generation_log = []
        self.mece_violations = []
        
    async def generate_recursive_subtopics(self, db, topic: Topic, user_id: int, depth: int = 0, max_depth: int = 5):
        """Recursively generate subtopics for a topic"""
        if self.generated_count >= self.target_count or depth >= max_depth:
            return
            
        print(f"\n{'  ' * depth}🌳 Processing: {topic.name} (Depth: {depth})")
        
        # Get or create user progress with competent level
        progress = await self._ensure_user_progress(db, user_id, topic.id)
        
        # Check existing children
        existing_children = await db.execute(
            select(Topic).where(Topic.parent_id == topic.id)
        )
        children = existing_children.scalars().all()
        
        if not children:
            # Generate subtopics
            print(f"{'  ' * depth}🎲 Generating subtopics for {topic.name}...")
            
            # Create user interests (empty for now)
            user_interests = []
            
            try:
                # Generate subtopics
                subtopics_data = await self.topic_generator.generate_subtopics(
                    db, topic, user_interests, count=None
                )
                
                if subtopics_data:
                    print(f"{'  ' * depth}✅ Generated {len(subtopics_data)} subtopics")
                    
                    # Create in database
                    created_topics = await self.topic_generator.create_topics_in_database(
                        db, subtopics_data, topic.id
                    )
                    
                    # Unlock for user
                    for subtopic in created_topics:
                        await self._unlock_topic_for_user(db, user_id, subtopic.id)
                    
                    await db.commit()
                    
                    self.generated_count += len(created_topics)
                    children = created_topics
                    
                    # Log generation
                    self.generation_log.append({
                        'parent': topic.name,
                        'parent_id': topic.id,
                        'depth': depth,
                        'children_count': len(created_topics),
                        'children': [t.name for t in created_topics],
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    print(f"{'  ' * depth}📊 Total generated so far: {self.generated_count}")
                else:
                    print(f"{'  ' * depth}⚠️ No subtopics generated for {topic.name}")
                    return
                    
            except Exception as e:
                print(f"{'  ' * depth}❌ Error generating for {topic.name}: {e}")
                await db.rollback()
                return
        else:
            print(f"{'  ' * depth}📋 Found {len(children)} existing children")
        
        # Store tree data
        self.tree_data[topic.id] = {
            'name': topic.name,
            'depth': depth,
            'children': [c.id for c in children],
            'parent_id': topic.parent_id
        }
        
        # Recursively process children
        for child in children:
            if self.generated_count >= self.target_count:
                break
            await self.generate_recursive_subtopics(db, child, user_id, depth + 1, max_depth)
    
    async def _ensure_user_progress(self, db, user_id: int, topic_id: int):
        """Ensure user has competent level progress for topic"""
        result = await db.execute(
            select(UserSkillProgress).where(
                UserSkillProgress.user_id == user_id,
                UserSkillProgress.topic_id == topic_id
            )
        )
        progress = result.scalar_one_or_none()
        
        if not progress:
            progress = UserSkillProgress(
                user_id=user_id,
                topic_id=topic_id,
                current_mastery_level="competent",
                mastery_level="competent",
                questions_answered=10,
                correct_answers=8,
                is_unlocked=True
            )
            db.add(progress)
            await db.flush()
        elif progress.current_mastery_level == "novice":
            progress.current_mastery_level = "competent"
            progress.mastery_level = "competent"
            progress.questions_answered = max(10, progress.questions_answered)
            
        return progress
    
    async def _unlock_topic_for_user(self, db, user_id: int, topic_id: int):
        """Unlock a topic for the user"""
        progress = UserSkillProgress(
            user_id=user_id,
            topic_id=topic_id,
            is_unlocked=True,
            current_mastery_level="novice",
            mastery_level="novice"
        )
        db.add(progress)
    
    def analyze_tree_structure(self):
        """Analyze the generated tree for MECE violations and structure"""
        print("\n" + "="*80)
        print("TREE STRUCTURE ANALYSIS")
        print("="*80)
        
        # Basic statistics
        depths = [node['depth'] for node in self.tree_data.values()]
        children_counts = [len(node['children']) for node in self.tree_data.values()]
        
        print(f"\n📊 BASIC STATISTICS:")
        print(f"Total nodes: {len(self.tree_data)}")
        print(f"Maximum depth: {max(depths) if depths else 0}")
        print(f"Average children per node: {sum(children_counts) / len(children_counts) if children_counts else 0:.2f}")
        print(f"Nodes by depth: {Counter(depths)}")
        
        # Check for MECE violations
        self._check_mece_violations()
        
        # Analyze topic name patterns
        self._analyze_naming_patterns()
        
        # Check for logical hierarchy
        self._check_logical_hierarchy()
        
        # Generate visualization
        self._visualize_tree_sample()
    
    def _check_mece_violations(self):
        """Check for MECE violations in the tree"""
        print(f"\n🔍 CHECKING MECE PRINCIPLES:")
        
        violations = []
        
        # Group nodes by parent
        parent_groups = defaultdict(list)
        for node_id, node in self.tree_data.items():
            if node['parent_id']:
                parent_groups[node['parent_id']].append((node_id, node['name']))
        
        # Check each sibling group
        for parent_id, siblings in parent_groups.items():
            parent_name = self.tree_data.get(parent_id, {}).get('name', 'Unknown')
            
            # Check for duplicate names
            names = [name.lower() for _, name in siblings]
            name_counts = Counter(names)
            for name, count in name_counts.items():
                if count > 1:
                    violations.append({
                        'type': 'duplicate',
                        'parent': parent_name,
                        'issue': f"Duplicate topic '{name}' appears {count} times"
                    })
            
            # Check for overlapping concepts
            for i, (id1, name1) in enumerate(siblings):
                for id2, name2 in siblings[i+1:]:
                    overlap = self._check_conceptual_overlap(name1, name2)
                    if overlap:
                        violations.append({
                            'type': 'overlap',
                            'parent': parent_name,
                            'issue': f"'{name1}' and '{name2}' have conceptual overlap: {overlap}"
                        })
            
            # Check for completeness (heuristic)
            if len(siblings) < 3 and parent_name != "Artificial Intelligence":
                violations.append({
                    'type': 'incomplete',
                    'parent': parent_name,
                    'issue': f"Only {len(siblings)} subtopics - may not be collectively exhaustive"
                })
        
        self.mece_violations = violations
        
        if violations:
            print(f"⚠️ Found {len(violations)} MECE violations:")
            for v in violations[:10]:  # Show first 10
                print(f"  - [{v['type'].upper()}] Under '{v['parent']}': {v['issue']}")
            if len(violations) > 10:
                print(f"  ... and {len(violations) - 10} more violations")
        else:
            print("✅ No MECE violations detected!")
    
    def _check_conceptual_overlap(self, name1: str, name2: str) -> str:
        """Check if two topic names have conceptual overlap"""
        name1_lower = name1.lower()
        name2_lower = name2.lower()
        
        # Check for subset relationships
        if name1_lower in name2_lower or name2_lower in name1_lower:
            return "subset relationship"
        
        # Check for common significant words
        words1 = set(name1_lower.split()) - {'of', 'and', 'the', 'in', 'for', 'with', 'to', 'a', 'an'}
        words2 = set(name2_lower.split()) - {'of', 'and', 'the', 'in', 'for', 'with', 'to', 'a', 'an'}
        
        common_words = words1 & words2
        if len(common_words) >= 2:
            return f"share words: {', '.join(common_words)}"
        
        # Check for known overlapping concepts
        overlap_pairs = [
            ('machine learning', 'deep learning'),
            ('supervised', 'unsupervised'),
            ('classification', 'prediction'),
            ('neural', 'network'),
            ('algorithm', 'method'),
            ('application', 'use case'),
            ('theory', 'theoretical'),
            ('practical', 'applied')
        ]
        
        for term1, term2 in overlap_pairs:
            if (term1 in name1_lower and term2 in name2_lower) or \
               (term2 in name1_lower and term1 in name2_lower):
                return f"related concepts: {term1}/{term2}"
        
        return ""
    
    def _analyze_naming_patterns(self):
        """Analyze naming patterns in the tree"""
        print(f"\n📝 NAMING PATTERN ANALYSIS:")
        
        all_names = [node['name'] for node in self.tree_data.values()]
        
        # Common prefixes/suffixes
        prefixes = Counter()
        suffixes = Counter()
        word_frequency = Counter()
        
        for name in all_names:
            words = name.split()
            if words:
                prefixes[words[0]] += 1
                suffixes[words[-1]] += 1
                word_frequency.update(words)
        
        print("\nMost common first words:")
        for word, count in prefixes.most_common(10):
            print(f"  - '{word}': {count} times")
        
        print("\nMost common last words:")
        for word, count in suffixes.most_common(10):
            print(f"  - '{word}': {count} times")
        
        print("\nMost frequent words overall:")
        for word, count in word_frequency.most_common(15):
            if word.lower() not in {'of', 'and', 'the', 'in', 'for', 'with', 'to', 'a', 'an'}:
                print(f"  - '{word}': {count} times")
    
    def _check_logical_hierarchy(self):
        """Check if the hierarchy is logically structured"""
        print(f"\n🏗️ LOGICAL HIERARCHY ANALYSIS:")
        
        issues = []
        
        for node_id, node in self.tree_data.items():
            if node['parent_id']:
                parent = self.tree_data.get(node['parent_id'])
                if parent:
                    # Check if child is more general than parent
                    if self._is_more_general(node['name'], parent['name']):
                        issues.append(f"'{node['name']}' seems more general than parent '{parent['name']}'")
                    
                    # Check depth appropriateness
                    if node['depth'] > 3 and any(word in node['name'].lower() for word in ['introduction', 'basics', 'fundamentals', 'overview']):
                        issues.append(f"Basic topic '{node['name']}' at depth {node['depth']} - should be higher")
        
        if issues:
            print(f"⚠️ Found {len(issues)} hierarchy issues:")
            for issue in issues[:10]:
                print(f"  - {issue}")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more issues")
        else:
            print("✅ Hierarchy appears logically structured!")
    
    def _is_more_general(self, child_name: str, parent_name: str) -> bool:
        """Check if child topic is more general than parent"""
        child_lower = child_name.lower()
        parent_lower = parent_name.lower()
        
        # Check if parent name is contained in child (usually means child is more specific)
        if parent_lower in child_lower:
            return False
        
        # Check for general terms in child
        general_terms = ['general', 'overview', 'introduction', 'all', 'complete', 'comprehensive']
        child_has_general = any(term in child_lower for term in general_terms)
        parent_has_general = any(term in parent_lower for term in general_terms)
        
        return child_has_general and not parent_has_general
    
    def _visualize_tree_sample(self):
        """Create a sample visualization of part of the tree"""
        print(f"\n📊 GENERATING TREE VISUALIZATION SAMPLE...")
        
        # Create a graph for a subset of the tree
        G = nx.DiGraph()
        
        # Add nodes and edges (limit to first 100 for visualization)
        for i, (node_id, node) in enumerate(list(self.tree_data.items())[:100]):
            G.add_node(node_id, label=node['name'][:20] + '...' if len(node['name']) > 20 else node['name'])
            if node['parent_id'] and node['parent_id'] in self.tree_data:
                G.add_edge(node['parent_id'], node_id)
        
        # Save graph statistics
        if G.number_of_nodes() > 0:
            print(f"Sample graph nodes: {G.number_of_nodes()}")
            print(f"Sample graph edges: {G.number_of_edges()}")
            
            # Calculate some graph metrics
            if nx.is_weakly_connected(G):
                print(f"Average shortest path length: {nx.average_shortest_path_length(G):.2f}")
            
            degrees = dict(G.degree())
            avg_degree = sum(degrees.values()) / len(degrees) if degrees else 0
            print(f"Average degree: {avg_degree:.2f}")
    
    def save_results(self):
        """Save analysis results to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save generation log
        with open(f"recursive_generation_log_{timestamp}.json", 'w') as f:
            json.dump({
                'summary': {
                    'total_generated': self.generated_count,
                    'total_nodes': len(self.tree_data),
                    'generation_log': self.generation_log,
                    'mece_violations': self.mece_violations
                },
                'tree_data': self.tree_data
            }, f, indent=2)
        
        print(f"\n💾 Results saved to recursive_generation_log_{timestamp}.json")
        
        # Save MECE violations report
        if self.mece_violations:
            with open(f"mece_violations_{timestamp}.txt", 'w') as f:
                f.write("MECE VIOLATIONS REPORT\n")
                f.write("=" * 80 + "\n\n")
                
                by_type = defaultdict(list)
                for v in self.mece_violations:
                    by_type[v['type']].append(v)
                
                for vtype, violations in by_type.items():
                    f.write(f"\n{vtype.upper()} VIOLATIONS ({len(violations)} total)\n")
                    f.write("-" * 40 + "\n")
                    for v in violations:
                        f.write(f"Parent: {v['parent']}\n")
                        f.write(f"Issue: {v['issue']}\n\n")
            
            print(f"💾 MECE violations saved to mece_violations_{timestamp}.txt")


async def main():
    """Main test function"""
    print("🚀 RECURSIVE SUBTOPIC GENERATION TEST")
    print("Target: Generate at least 1000 subtopics")
    print("="*80)
    
    generator = RecursiveSubtopicGenerator()
    
    async with AsyncSessionLocal() as db:
        # Get AI root topic
        result = await db.execute(
            select(Topic).where(Topic.name == "Artificial Intelligence")
        )
        ai_topic = result.scalar_one_or_none()
        
        if not ai_topic:
            print("❌ AI topic not found!")
            return
        
        print(f"✅ Starting with root topic: {ai_topic.name} (ID: {ai_topic.id})")
        
        # Start recursive generation
        start_time = time.time()
        await generator.generate_recursive_subtopics(db, ai_topic, user_id=1, max_depth=6)
        generation_time = time.time() - start_time
        
        print(f"\n⏱️ Generation completed in {generation_time:.2f} seconds")
        print(f"📊 Total subtopics generated: {generator.generated_count}")
        
        # Load full tree from database for analysis
        all_topics_result = await db.execute(select(Topic))
        all_topics = all_topics_result.scalars().all()
        
        print(f"📊 Total topics in database: {len(all_topics)}")
        
        # Rebuild tree data with all topics
        generator.tree_data = {}
        for topic in all_topics:
            generator.tree_data[topic.id] = {
                'name': topic.name,
                'depth': 0,  # Will calculate
                'children': [],
                'parent_id': topic.parent_id
            }
        
        # Calculate depths and children
        for topic in all_topics:
            if topic.parent_id and topic.parent_id in generator.tree_data:
                generator.tree_data[topic.parent_id]['children'].append(topic.id)
        
        # Calculate depths
        def calculate_depth(topic_id, depth=0):
            generator.tree_data[topic_id]['depth'] = depth
            for child_id in generator.tree_data[topic_id]['children']:
                calculate_depth(child_id, depth + 1)
        
        calculate_depth(ai_topic.id)
        
        # Analyze the tree
        generator.analyze_tree_structure()
        
        # Save results
        generator.save_results()
        
        print("\n✅ Test completed!")


if __name__ == "__main__":
    asyncio.run(main())