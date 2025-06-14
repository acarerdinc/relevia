#!/usr/bin/env python3
"""
Check total topics in database and analyze the tree
"""
import asyncio
from sqlalchemy import select, func
from db.database import AsyncSessionLocal
from db.models import Topic
from collections import defaultdict, Counter
import json


async def analyze_topics():
    async with AsyncSessionLocal() as db:
        # Count total topics
        count_result = await db.execute(select(func.count(Topic.id)))
        total_count = count_result.scalar()
        print(f"📊 Total topics in database: {total_count}")
        
        # Get all topics
        all_topics_result = await db.execute(select(Topic))
        all_topics = all_topics_result.scalars().all()
        
        # Build tree structure
        tree_data = {}
        parent_groups = defaultdict(list)
        
        for topic in all_topics:
            tree_data[topic.id] = {
                'name': topic.name,
                'parent_id': topic.parent_id,
                'children': []
            }
            if topic.parent_id:
                parent_groups[topic.parent_id].append(topic)
        
        # Calculate depths
        def calculate_depth(topic_id, visited=None):
            if visited is None:
                visited = set()
            if topic_id in visited:
                return 0
            visited.add(topic_id)
            
            topic = tree_data.get(topic_id)
            if not topic or not topic['parent_id']:
                return 0
            return 1 + calculate_depth(topic['parent_id'], visited)
        
        depths = []
        for topic_id in tree_data:
            depth = calculate_depth(topic_id)
            tree_data[topic_id]['depth'] = depth
            depths.append(depth)
        
        # Analyze structure
        print(f"\n📊 TREE STRUCTURE:")
        print(f"Maximum depth: {max(depths) if depths else 0}")
        print(f"Depth distribution: {Counter(depths)}")
        
        # Check for MECE violations
        print(f"\n🔍 CHECKING FOR OBVIOUS MECE VIOLATIONS:")
        
        violations = []
        for parent_id, siblings in parent_groups.items():
            parent_name = tree_data.get(parent_id, {}).get('name', 'Unknown')
            
            # Check for duplicates
            names = [s.name.lower() for s in siblings]
            name_counts = Counter(names)
            for name, count in name_counts.items():
                if count > 1:
                    violations.append(f"DUPLICATE: '{name}' appears {count} times under '{parent_name}'")
            
            # Check for very similar names
            for i, sib1 in enumerate(siblings):
                for sib2 in siblings[i+1:]:
                    name1 = sib1.name.lower()
                    name2 = sib2.name.lower()
                    
                    # Check subset relationships
                    if name1 in name2 or name2 in name1:
                        violations.append(f"SUBSET: '{sib1.name}' and '{sib2.name}' under '{parent_name}'")
                    
                    # Check word overlap
                    words1 = set(name1.split()) - {'of', 'and', 'the', 'in', 'for', 'with', 'to', 'a', 'an'}
                    words2 = set(name2.split()) - {'of', 'and', 'the', 'in', 'for', 'with', 'to', 'a', 'an'}
                    common = words1 & words2
                    if len(common) >= 3:
                        violations.append(f"OVERLAP: '{sib1.name}' and '{sib2.name}' share {len(common)} words under '{parent_name}'")
        
        if violations:
            print(f"⚠️ Found {len(violations)} potential violations:")
            for v in violations[:20]:
                print(f"  - {v}")
            if len(violations) > 20:
                print(f"  ... and {len(violations) - 20} more")
        else:
            print("✅ No obvious violations found!")
        
        # Sample some branches
        print(f"\n🌳 SAMPLE BRANCHES:")
        
        def print_branch(topic_id, indent=0, max_depth=3):
            if indent > max_depth:
                return
            topic = tree_data.get(topic_id)
            if topic:
                print(f"{'  ' * indent}- {topic['name']}")
                children = [t.id for t in all_topics if t.parent_id == topic_id]
                for child_id in children[:3]:  # Show first 3 children
                    print_branch(child_id, indent + 1, max_depth)
                if len(children) > 3:
                    print(f"{'  ' * (indent + 1)}... and {len(children) - 3} more")
        
        # Find AI topic
        ai_topic = next((t for t in all_topics if t.name == "Artificial Intelligence" and not t.parent_id), None)
        if ai_topic:
            print("\nArtificial Intelligence branch:")
            print_branch(ai_topic.id, max_depth=4)


if __name__ == "__main__":
    asyncio.run(analyze_topics())