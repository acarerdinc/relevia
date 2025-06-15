"""
Mastery Levels Configuration
Defines the progression system for topic mastery
"""

from enum import Enum
from typing import Dict, List

class MasteryLevel(str, Enum):
    """Mastery levels from novice to master (PhD level)"""
    NOVICE = "novice"
    COMPETENT = "competent" 
    PROFICIENT = "proficient"
    EXPERT = "expert"
    MASTER = "master"

# Mastery level progression order
MASTERY_PROGRESSION = [
    MasteryLevel.NOVICE,
    MasteryLevel.COMPETENT,
    MasteryLevel.PROFICIENT,
    MasteryLevel.EXPERT,
    MasteryLevel.MASTER
]

# Correct answers required to advance to next level
QUESTIONS_PER_LEVEL = {
    MasteryLevel.NOVICE: 8,      # 8 correct answers to become competent
    MasteryLevel.COMPETENT: 12,  # 12 correct answers to become proficient
    MasteryLevel.PROFICIENT: 15, # 15 correct answers to become expert
    MasteryLevel.EXPERT: 20,     # 20 correct answers to become master
    MasteryLevel.MASTER: 0       # Master is final level
}

# Accuracy threshold to advance (percentage) - NO LONGER USED
# Kept for reference but system now uses correct answer count only
ACCURACY_THRESHOLD = {
    MasteryLevel.NOVICE: 0.70,     # 70% accuracy needed
    MasteryLevel.COMPETENT: 0.75,  # 75% accuracy needed  
    MasteryLevel.PROFICIENT: 0.80, # 80% accuracy needed
    MasteryLevel.EXPERT: 0.85,     # 85% accuracy needed
    MasteryLevel.MASTER: 0.90      # 90% accuracy needed (for maintaining)
}

# Minimum level required for tree navigation (unlocking new topics)
TREE_NAVIGATION_THRESHOLD = MasteryLevel.COMPETENT

# Mastery level descriptions
MASTERY_DESCRIPTIONS = {
    MasteryLevel.NOVICE: {
        "title": "Novice",
        "description": "Basic understanding of fundamental concepts",
        "equivalent": "Undergraduate introduction level"
    },
    MasteryLevel.COMPETENT: {
        "title": "Competent", 
        "description": "Solid grasp of core principles and can apply them",
        "equivalent": "Undergraduate advanced level"
    },
    MasteryLevel.PROFICIENT: {
        "title": "Proficient",
        "description": "Deep understanding with ability to analyze and synthesize",
        "equivalent": "Graduate level"
    },
    MasteryLevel.EXPERT: {
        "title": "Expert",
        "description": "Advanced mastery with deep insights and edge case knowledge",
        "equivalent": "Advanced graduate/industry expert"
    },
    MasteryLevel.MASTER: {
        "title": "Master",
        "description": "Research-level expertise with cutting-edge knowledge",
        "equivalent": "PhD/Research scientist level"
    }
}

def get_next_mastery_level(current_level: MasteryLevel) -> MasteryLevel | None:
    """Get the next mastery level, or None if at max level"""
    try:
        current_index = MASTERY_PROGRESSION.index(current_level)
        if current_index < len(MASTERY_PROGRESSION) - 1:
            return MASTERY_PROGRESSION[current_index + 1]
        return None
    except ValueError:
        return MasteryLevel.NOVICE

def can_advance_mastery(questions_answered: int, correct_answers: int, current_level: MasteryLevel) -> bool:
    """Check if user can advance to next mastery level based on correct answers only"""
    if current_level == MasteryLevel.MASTER:
        return False
        
    required_correct_answers = QUESTIONS_PER_LEVEL[current_level]
    
    # Just check if they have enough correct answers
    return correct_answers >= required_correct_answers

def get_mastery_progress(questions_answered: int, current_level: MasteryLevel) -> Dict:
    """Get progress towards next mastery level"""
    if current_level == MasteryLevel.MASTER:
        return {
            "progress_percent": 100,
            "questions_needed": 0,
            "is_max_level": True
        }
    
    required_questions = QUESTIONS_PER_LEVEL[current_level]
    progress_percent = min(100, (questions_answered / required_questions) * 100)
    questions_needed = max(0, required_questions - questions_answered)
    
    return {
        "progress_percent": progress_percent,
        "questions_needed": questions_needed,
        "is_max_level": False
    }