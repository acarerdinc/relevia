-- Insert test users into existing Supabase database
-- Password: fenapass1
-- Password: ordekzeze1  
-- Password: zazapass1

INSERT INTO users (email, username, hashed_password, is_active) VALUES
('info@acarerdinc.com', 'acarerdinc', '$2b$12$MpsuBqqnS68EusawjQpNR.XfsBU10ZxMGYJOY2OZH8Q9CCRx2aaLu', true),
('ogulcancelik@gmail.com', 'ogulcancelik', '$2b$12$HJ.Cr5.6e.Hdu/fthvsHNeFzA7Hd4AH3Y0ahmTYiho.TjKTIt5Pie', true),
('begumcitamak@gmail.com', 'begumcitamak', '$2b$12$KICM8SZptoM.1o3qygwneO1OXpOUho7KixeB6mQcp4tZfv1aVzYjO', true)
ON CONFLICT (email) DO NOTHING;