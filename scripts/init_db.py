#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from database import init_db, SessionLocal
from models import SearchTerm, Profile, BlockedCompany

init_db()

db = SessionLocal()
# Seed search terms
default_terms = [
    ('IT Systems Administrator', 'user'),
    ('Endpoint Engineer', 'user'),
    ('Desktop Support Engineer', 'user'),
]
for term, source in default_terms:
    existing = db.query(SearchTerm).filter_by(term=term).first()
    if not existing:
        db.add(SearchTerm(term=term, source=source))

# Seed blocked companies
for name in ['WSI', 'Marion Body Works', 'Marion BodyWorks']:
    existing = db.query(BlockedCompany).filter_by(name=name).first()
    if not existing:
        db.add(BlockedCompany(name=name))

# Seed profile if empty
if not db.query(Profile).first():
    db.add(Profile())

db.commit()
db.close()
print("Database initialized with seed data.")
