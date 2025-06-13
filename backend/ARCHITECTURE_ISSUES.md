# Critical Architecture Issues

## 1. Broken Answer Validation

### Current Flow (BROKEN)
```
Display Question:
1. Load from DB: ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"]
2. Shuffle:      ["B) Option 2", "D) Option 4", "A) Option 1", "C) Option 3"]  
3. Add Debug:    ["B) Option 2", "✓ D) Option 4", "A) Option 1", "C) Option 3"]
4. User sees shuffled version with debug markers

Submit Answer:
1. User selects index 1 (which shows "✓ D) Option 4" to them)
2. Backend checks question.options[1] = "B) Option 2" (from unshuffled DB)
3. Answer marked wrong even though user selected the marked correct answer!
```

### Why It's Broken
- No state persistence between display and validation
- Shuffling happens on display but validation uses original order
- Debug symbols are added to display but validation doesn't know about them

## 2. Code Duplication

### Shuffle Implementation (Duplicated)
- `services/quiz_service.py`: _shuffle_question_options()
- `services/adaptive_question_selector.py`: _shuffle_question_options()

### Answer Validation (Duplicated)
- `services/quiz_service.py`: submit_answer()
- `services/adaptive_quiz_service.py`: submit_adaptive_answer()

### Question Formatting (Scattered)
- Regular quiz path
- Adaptive selection path
- Generated question path
- Fallback question path

## 3. Solutions

### Quick Fix (Still Flawed)
Store shuffle mapping in QuizQuestion record:
```python
# When displaying
quiz_question.shuffle_map = {"0": 2, "1": 0, "2": 3, "3": 1}  # old->new index
# When validating
real_index = quiz_question.shuffle_map[str(user_answer)]
```

### Proper Fix (Modular Architecture)
1. Create `QuestionFormatter` service (✓ created)
2. Store formatted state or recreate deterministically
3. Single source of truth for all transformations
4. Validate against what user actually saw

### Benefits of Proper Architecture
- One place to add features (debug mode, hints, etc.)
- Correct answer validation
- Works across all strategies
- Easier testing
- Less code duplication