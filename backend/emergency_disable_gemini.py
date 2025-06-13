#!/usr/bin/env python3
"""
Emergency script to disable Gemini AI generation temporarily
When Gemini API is down/slow, this forces the system to use only fallback questions
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

def disable_gemini_temporarily():
    """Modify the question selector to skip AI generation"""
    
    selector_file = Path(__file__).parent / "services" / "adaptive_question_selector.py"
    
    # Read current content
    with open(selector_file, 'r') as f:
        content = f.read()
    
    # Check if already disabled
    if "# EMERGENCY GEMINI BYPASS" in content:
        print("🚫 Gemini AI generation is already disabled")
        return
    
    # Add emergency bypass
    emergency_code = '''
            # EMERGENCY GEMINI BYPASS - Remove this block when Gemini is working
            print(f"⚡ EMERGENCY: Skipping Gemini due to API issues, using fallback for {topic['name']}")
            return self._create_fallback_question(topic, target_difficulty)
            # END EMERGENCY BYPASS
            '''
    
    # Insert emergency bypass right after the try block
    insertion_point = content.find('try:\n                # Set a shorter timeout for Gemini API call')
    if insertion_point != -1:
        # Insert after the try line
        try_line_end = content.find('\n', insertion_point) + 1
        new_content = content[:try_line_end] + emergency_code + content[try_line_end:]
        
        # Write back
        with open(selector_file, 'w') as f:
            f.write(new_content)
        
        print("🚫 EMERGENCY: Disabled Gemini AI generation")
        print("✅ System will now use fast fallback questions only")
        print("🔄 Restart your backend server to apply changes")
        print("⚠️  Remember to run 'python enable_gemini.py' when Gemini is working again")
    else:
        print("❌ Could not find insertion point in code")

def enable_gemini():
    """Re-enable Gemini AI generation"""
    
    selector_file = Path(__file__).parent / "services" / "adaptive_question_selector.py"
    
    # Read current content
    with open(selector_file, 'r') as f:
        content = f.read()
    
    # Check if disabled
    if "# EMERGENCY GEMINI BYPASS" not in content:
        print("✅ Gemini AI generation is already enabled")
        return
    
    # Remove emergency bypass block
    start_marker = "# EMERGENCY GEMINI BYPASS"
    end_marker = "# END EMERGENCY BYPASS"
    
    start_pos = content.find(start_marker)
    if start_pos != -1:
        end_pos = content.find(end_marker) + len(end_marker)
        
        # Remove the emergency block
        new_content = content[:start_pos] + content[end_pos:]
        
        # Clean up extra newlines
        new_content = new_content.replace('\n\n\n', '\n\n')
        
        # Write back
        with open(selector_file, 'w') as f:
            f.write(new_content)
        
        print("✅ Re-enabled Gemini AI generation")
        print("🔄 Restart your backend server to apply changes")
    else:
        print("❌ Could not find emergency bypass block")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "enable":
        enable_gemini()
    else:
        disable_gemini_temporarily()