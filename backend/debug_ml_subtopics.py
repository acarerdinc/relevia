import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from db.models import Topic, UserSkillProgress, DynamicTopicUnlock

async def debug_ml_subtopics():
    # Create database connection
    engine = create_async_engine("sqlite+aiosqlite:///relevia.db", echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. Find Machine Learning topic
        ml_result = await db.execute(
            select(Topic).where(Topic.name == "Machine Learning")
        )
        ml_topic = ml_result.scalar_one_or_none()
        
        if not ml_topic:
            print("❌ Machine Learning topic not found in database!")
            return
        
        print(f"✅ Found Machine Learning topic: ID={ml_topic.id}, Parent_ID={ml_topic.parent_id}")
        print(f"   Description: {ml_topic.description}")
        print()
        
        # 2. Check if Machine Learning has any children
        children_result = await db.execute(
            select(Topic).where(Topic.parent_id == ml_topic.id).order_by(Topic.name)
        )
        children = children_result.scalars().all()
        
        print(f"📊 Machine Learning has {len(children)} child topics in the database:")
        print("-" * 80)
        
        if not children:
            print("   ⚠️  NO CHILDREN FOUND! This explains why they don't show in the tree.")
            print("   Machine Learning should generate subtopics when user reaches Competent level.")
        else:
            # 3. For each child, check UserSkillProgress
            for child in children:
                print(f"\n🔸 Child Topic: {child.name} (ID={child.id})")
                print(f"   Difficulty: {child.difficulty_min}-{child.difficulty_max}")
                
                # Check UserSkillProgress for user_id=1 (default user)
                progress_result = await db.execute(
                    select(UserSkillProgress).where(
                        UserSkillProgress.topic_id == child.id,
                        UserSkillProgress.user_id == 1
                    )
                )
                progress = progress_result.scalar_one_or_none()
                
                if progress:
                    print(f"   ✅ UserSkillProgress exists:")
                    print(f"      - is_unlocked: {progress.is_unlocked}")
                    print(f"      - mastery_level: {progress.current_mastery_level}")
                    print(f"      - questions_answered: {progress.questions_answered}")
                    print(f"      - unlocked_at: {progress.unlocked_at}")
                else:
                    print(f"   ❌ No UserSkillProgress record found for user_id=1")
                
                # Check DynamicTopicUnlock
                unlock_result = await db.execute(
                    select(DynamicTopicUnlock).where(
                        DynamicTopicUnlock.unlocked_topic_id == child.id,
                        DynamicTopicUnlock.user_id == 1
                    )
                )
                unlock = unlock_result.scalar_one_or_none()
                
                if unlock:
                    print(f"   ✅ DynamicTopicUnlock exists:")
                    print(f"      - parent_topic_id: {unlock.parent_topic_id}")
                    print(f"      - unlock_trigger: {unlock.unlock_trigger}")
                    print(f"      - unlocked_at: {unlock.unlocked_at}")
                else:
                    print(f"   ❌ No DynamicTopicUnlock record found for user_id=1")
        
        print("\n" + "=" * 80)
        
        # 4. Check user's progress on Machine Learning itself
        ml_progress_result = await db.execute(
            select(UserSkillProgress).where(
                UserSkillProgress.topic_id == ml_topic.id,
                UserSkillProgress.user_id == 1
            )
        )
        ml_progress = ml_progress_result.scalar_one_or_none()
        
        if ml_progress:
            print(f"\n📈 Machine Learning Progress for user_id=1:")
            print(f"   - Current Mastery Level: {ml_progress.current_mastery_level}")
            print(f"   - Questions Answered: {ml_progress.questions_answered}")
            print(f"   - Correct Answers: {ml_progress.correct_answers}")
            print(f"   - Is Unlocked: {ml_progress.is_unlocked}")
            print(f"   - Proficiency Threshold Met: {ml_progress.proficiency_threshold_met}")
            print(f"   - Mastery Questions: {ml_progress.mastery_questions_answered}")
        else:
            print("\n❌ No progress record found for Machine Learning!")

if __name__ == "__main__":
    asyncio.run(debug_ml_subtopics())