20250407:
Confirmed Starter always read as "True" (won't exclude any players despite minimum starters constraint)
File: lineup_importer.py
Before: 'is_confirmed_starter': bool(row.get('Confirmed Starter')),
After:  'is_confirmed_starter': bool(int(row.get('Confirmed Starter'))),
