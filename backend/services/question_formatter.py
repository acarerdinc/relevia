"""
Centralized Question Formatting Service
Handles all question transformations in one place for consistency
"""
import random
from typing import List, Dict, Tuple, Optional

class QuestionFormatter:
    """
    Centralized service for formatting questions consistently across all strategies.
    Handles shuffling, debug markers, and answer validation.
    """
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
    
    def format_question(self, question_data: Dict) -> Dict:
        """
        Format a question for display, applying all necessary transformations.
        
        Args:
            question_data: Raw question data with at least:
                - options: List of answer options
                - correct_answer: The correct answer text
                
        Returns:
            Formatted question data with:
                - shuffled options
                - debug markers (if enabled)
                - answer mapping for validation
        """
        options = question_data.get('options', [])
        correct_answer = question_data.get('correct_answer', '')
        
        # Shuffle options
        shuffled_options, shuffled_correct_answer, answer_map = self._shuffle_options(
            options, correct_answer
        )
        
        # Apply debug marker if enabled
        if self.debug_mode:
            shuffled_options = self._add_debug_marker(
                shuffled_options, shuffled_correct_answer
            )
        
        # Return formatted question with answer mapping
        formatted_data = question_data.copy()
        formatted_data['options'] = shuffled_options
        formatted_data['_answer_map'] = answer_map  # Internal use for validation
        formatted_data['_correct_index'] = answer_map[correct_answer]  # Index of correct answer
        
        return formatted_data
    
    def validate_answer(self, 
                       user_answer: Optional[str | int], 
                       formatted_question: Dict,
                       original_question: Dict) -> Tuple[bool, str]:
        """
        Validate user's answer against the formatted question.
        
        Args:
            user_answer: User's answer (index or text)
            formatted_question: The formatted question shown to user
            original_question: Original question from database
            
        Returns:
            Tuple of (is_correct, selected_option_text)
        """
        if user_answer is None:
            return False, ""
        
        # Get the correct answer index from formatted question
        correct_index = formatted_question.get('_correct_index', -1)
        formatted_options = formatted_question.get('options', [])
        
        # Handle index-based answers
        if isinstance(user_answer, int) or (isinstance(user_answer, str) and user_answer.isdigit()):
            option_index = int(user_answer)
            
            if 0 <= option_index < len(formatted_options):
                # User selected this index
                is_correct = (option_index == correct_index)
                selected_text = formatted_options[option_index]
                
                # Remove debug marker for comparison if present
                if self.debug_mode and selected_text.startswith("✓ "):
                    selected_text = selected_text[2:]
                
                return is_correct, selected_text
            else:
                return False, ""
        
        # Handle text-based answers (legacy)
        # This is more complex with shuffled options
        return self._validate_text_answer(user_answer, formatted_question, original_question)
    
    def _shuffle_options(self, options: List[str], correct_answer: str) -> Tuple[List[str], str, Dict[str, int]]:
        """
        Shuffle options and track the mapping.
        
        Returns:
            Tuple of (shuffled_options, correct_answer_text, answer_mapping)
        """
        if not options:
            return [], correct_answer, {}
        
        # Create a copy to avoid modifying original
        options_copy = options.copy()
        
        # Find correct answer in options
        correct_index = self._find_correct_index(options_copy, correct_answer)
        
        if correct_index is None:
            # Correct answer not found in options - shouldn't happen
            print(f"Warning: Correct answer '{correct_answer}' not found in options")
            return options_copy, correct_answer, {}
        
        # Create index mapping
        indices = list(range(len(options_copy)))
        random.shuffle(indices)
        
        # Apply shuffle
        shuffled_options = [options_copy[i] for i in indices]
        
        # Find where correct answer ended up
        new_correct_index = indices.index(correct_index)
        correct_answer_text = shuffled_options[new_correct_index]
        
        # Create answer mapping (original text -> new index)
        answer_map = {options_copy[i]: indices.index(i) for i in range(len(options_copy))}
        
        return shuffled_options, correct_answer_text, answer_map
    
    def _find_correct_index(self, options: List[str], correct_answer: str) -> Optional[int]:
        """Find index of correct answer in options, handling various formats."""
        # Try exact match first
        for i, option in enumerate(options):
            if option == correct_answer:
                return i
        
        # Try case-insensitive match
        for i, option in enumerate(options):
            if option.strip().lower() == correct_answer.strip().lower():
                return i
        
        # Try matching just the text part (for "A) text" format)
        if len(correct_answer.strip()) == 1 and correct_answer.strip().upper() in 'ABCD':
            target_letter = correct_answer.strip().upper()
            for i, option in enumerate(options):
                if option.strip() and option.strip()[0].upper() == target_letter:
                    return i
        
        return None
    
    def _add_debug_marker(self, options: List[str], correct_answer: str) -> List[str]:
        """Add debug marker to correct option."""
        marked_options = options.copy()
        
        for i, option in enumerate(marked_options):
            if option == correct_answer:
                marked_options[i] = "✓ " + option
                break
        
        return marked_options
    
    def _validate_text_answer(self, user_answer: str, formatted_question: Dict, original_question: Dict) -> Tuple[bool, str]:
        """Validate text-based answer (legacy support)."""
        # This is complex with shuffled options
        # For now, return false to encourage index-based answers
        return False, user_answer

# Global instance
question_formatter = QuestionFormatter(debug_mode=False)