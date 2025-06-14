#!/usr/bin/env python3
"""Generate password hashes for test users"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

users = [
    ("info@acarerdinc.com", "fenapass1"),
    ("ogulcancelik@gmail.com", "ordekzeze1"),
    ("begumcitamak@gmail.com", "zazapass1")
]

print("Password hashes for SQL insertion:\n")
for email, password in users:
    hashed = pwd_context.hash(password)
    print(f"-- {email} / {password}")
    print(f"'{hashed}'\n")