NEVER EVER USE DIRECTLY AI RELATED FILTERS OR RULES IN THE CODE SINCE WE MIGHT CHANGE THE ROOT TOPIC TO SOME OTHER TOPIC IN THE FUTURE.
Never use fallback mechanisms unless explicitly requested.
Avoid temporary fixes. When the user gives an example error, find the root cause and fix it.
Don't create solutions for specific examples for bugs, find the root cause and fix the general issue.
NEVER restart the backend server. It automatically detects changes anyway. If you need to start the server tell the user to do it.
ALWAYS WORK ON DEV BRANCH! NEVER WORK ON MAIN BRANCH!

VERY IMPORTANT:
    - Never commit passwords, even for test users
    - Use environment variables for all sensitive data
    - Add a .gitignore entry for any files that might contain secrets