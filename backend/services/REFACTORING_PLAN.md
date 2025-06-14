# Question Handling Refactoring Plan

## Current Problems

1. **Answer Validation is Broken**
   - Questions are shuffled when displayed to user
   - But answer checking compares against original database options
   - Debug symbols break answer matching

2. **Code Duplication**
   - Question shuffling implemented in:
     - quiz_service.py (_shuffle_question_options)
     - adaptive_question_selector.py (_shuffle_question_options)
   - Answer validation logic duplicated in:
     - quiz_service.py (submit_answer)
     - adaptive_quiz_service.py (submit_adaptive_answer)

3. **Lack of Modularity**
   - Each strategy requires separate implementation
   - Adding features (like debug symbols) requires changes in multiple places
   - No single source of truth for question formatting

## Solution: Centralized Question Formatting

### 1. QuestionFormatter Service (Created)
```python
# services/question_formatter.py
- format_question(): Handles all transformations
- validate_answer(): Validates against formatted question
- Tracks shuffle mapping for correct validation
```

### 2. Integration Points

#### A. When Displaying Questions
Replace all shuffle logic with:
```python
from services.question_formatter import question_formatter

# In any service that returns questions
formatted_question = question_formatter.format_question({
    'options': question.options,
    'correct_answer': question.correct_answer,
    ...other_fields
})
```

#### B. When Validating Answers
Replace answer checking logic with:
```python
# Store formatted question in session or recreate it
is_correct, selected_text = question_formatter.validate_answer(
    user_answer, 
    formatted_question,
    original_question
)
```

### 3. Benefits

1. **Single Implementation**
   - One place to implement shuffling
   - One place to add debug symbols
   - One place to handle answer formats

2. **Correct Answer Validation**
   - Tracks shuffle mapping
   - Validates against what user actually saw
   - Handles all answer formats consistently

3. **Easy Feature Addition**
   - Toggle debug mode: `question_formatter.debug_mode = True/False`
   - Add new transformations in one place
   - Works automatically for all strategies

### 4. Migration Path

Phase 1: Create QuestionFormatter ✓
Phase 2: Update quiz_service.py to use formatter
Phase 3: Update adaptive services to use formatter
Phase 4: Remove duplicate shuffle implementations
Phase 5: Add configuration for debug mode

### 5. Example Usage

```python
# Before (broken)
shuffled_options, _ = self._shuffle_question_options(options, correct)
# ... later in submit_answer
selected_option = question.options[index]  # Wrong! Uses unshuffled options

# After (correct)
formatted = question_formatter.format_question(question_data)
# ... later in submit_answer
is_correct, _ = question_formatter.validate_answer(index, formatted, question)