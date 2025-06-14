# Frontend Mastery Display API Guide

## Problem
The UI is showing "0 questions answered at novice level" or no number at all, when it should show "8 correct answers at novice level".

## Root Cause
The backend is sending the correct data, but the frontend is not displaying it. The frontend appears to be looking for a field that doesn't exist or is not properly extracting the data.

## Available API Fields

### Progress Endpoint: `/api/v1/progress/user/{user_id}`

For each topic in the response, the following mastery fields are available:

#### Simple Direct Fields (Recommended)
```javascript
{
  // Direct access to correct answers for each level
  "novice_correct_answers": 8,
  "competent_correct_answers": 1,
  "proficient_correct_answers": 0,
  "expert_correct_answers": 0,
  "master_correct_answers": 0,
  
  // Current level info
  "current_mastery_level": "competent",
  "correct_answers_at_current_level": 1,
}
```

#### Object-based Fields
```javascript
{
  // Object with all levels
  "mastery_questions_answered": {
    "novice": 8,
    "competent": 1,
    "proficient": 0,
    "expert": 0,
    "master": 0
  },
  
  // Alias for the same data
  "mastery_correct_answers": {
    "novice": 8,
    "competent": 1,
    "proficient": 0,
    "expert": 0,
    "master": 0
  }
}
```

## How to Fix the Frontend Display

### Option 1: Use Direct Fields
```javascript
// To display "8 correct answers at novice level"
const noviceCorrectAnswers = topic.novice_correct_answers; // Returns: 8
```

### Option 2: Use Object Fields
```javascript
// To display "8 correct answers at novice level"
const noviceCorrectAnswers = topic.mastery_questions_answered.novice; // Returns: 8
// OR
const noviceCorrectAnswers = topic.mastery_correct_answers.novice; // Returns: 8
```

### Option 3: Dynamic Based on Current Level
```javascript
// To display correct answers for the current level
const currentLevel = topic.current_mastery_level; // "competent"
const correctAnswersAtLevel = topic.correct_answers_at_current_level; // 1

// Or dynamically:
const correctAnswers = topic.mastery_correct_answers[currentLevel]; // 1
```

## Required Frontend Changes

1. **Update the field reference** - Use one of the available fields above instead of whatever field the frontend is currently trying to access.

2. **Change the display text** - Update from "questions answered" to "correct answers" to reflect the new simplified system.

3. **Example React/Vue component fix**:
```javascript
// WRONG (what might be happening now)
<span>{topic.questions_at_novice_level || 0} questions answered at novice level</span>

// CORRECT
<span>{topic.novice_correct_answers} correct answers at novice level</span>
```

## Testing

After making the frontend changes, the UI should display:
- "8 correct answers at novice level" (not "0 questions answered")
- "1 correct answer at competent level" (for the current level)

## All Available Endpoints with Mastery Info

1. `/api/v1/progress/user/{user_id}` - Main progress with all fields
2. `/api/v1/mastery/user/{user_id}/overview` - Mastery-specific overview
3. `/api/v1/mastery/user/{user_id}/topic/{topic_id}` - Individual topic mastery
4. `/api/v1/progress/topic/{topic_id}/details?user_id={user_id}` - Topic details with mastery
5. `/api/v1/quiz/question/{session_id}` - Question response includes topic_progress
6. `/api/v1/adaptive/question/{session_id}` - Adaptive question with topic_progress

All endpoints now include the correct answer counts in multiple formats for maximum compatibility.