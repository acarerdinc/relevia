from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Generate hash for the password you want
password = input("Enter password to hash: ")
hashed = pwd_context.hash(password)

print(f"\nPassword: {password}")
print(f"Hash: {hashed}")
print(f"\nSQL to update user:")
print(f"UPDATE users SET hashed_password = '{hashed}' WHERE email = 'info@acarerdinc.com';")