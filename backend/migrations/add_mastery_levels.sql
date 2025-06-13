-- Add mastery levels to the system
-- Migration: Add Mastery Levels Support

-- Add mastery_level to user_skill_progress
ALTER TABLE user_skill_progress ADD COLUMN IF NOT EXISTS mastery_level VARCHAR(20) DEFAULT 'novice';

-- Add mastery_level to quiz_sessions  
ALTER TABLE quiz_sessions ADD COLUMN IF NOT EXISTS mastery_level VARCHAR(20) DEFAULT 'novice';

-- Add mastery_level to questions
ALTER TABLE questions ADD COLUMN IF NOT EXISTS mastery_level VARCHAR(20) DEFAULT 'novice';

-- Add mastery tracking columns to user_skill_progress
ALTER TABLE user_skill_progress ADD COLUMN IF NOT EXISTS mastery_questions_answered JSONB DEFAULT '{"novice": 0, "competent": 0, "proficient": 0, "expert": 0, "master": 0}';
ALTER TABLE user_skill_progress ADD COLUMN IF NOT EXISTS current_mastery_level VARCHAR(20) DEFAULT 'novice';

-- Create index for efficient mastery level queries
CREATE INDEX IF NOT EXISTS idx_questions_mastery_level ON questions(mastery_level);
CREATE INDEX IF NOT EXISTS idx_user_skill_progress_mastery ON user_skill_progress(current_mastery_level);

-- Update existing records to have default mastery level
UPDATE user_skill_progress SET mastery_level = 'novice' WHERE mastery_level IS NULL;
UPDATE quiz_sessions SET mastery_level = 'novice' WHERE mastery_level IS NULL;
UPDATE questions SET mastery_level = 'novice' WHERE mastery_level IS NULL;