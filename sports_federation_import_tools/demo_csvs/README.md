Demo CSVs for sports_federation_import_tools

Files included:
- clubs.csv: Columns = name,email,phone,city
- teams.csv: Columns = club_name,team_name
- players.csv: Columns = name,birth_date,club_name
- tournament_participants.csv: Columns = tournament_name,team_name

Recommended import order:
1. clubs.csv — create clubs first (required for teams/players)
2. teams.csv — creates teams, references club by `club_name`
3. players.csv — creates players, optional `birth_date` (YYYY-MM-DD) and `club_name`
4. tournament_participants.csv — registers teams for tournaments

Notes:
- Date format: use YYYY-MM-DD for `birth_date`.
- Files must be UTF-8 encoded. If you get encoding issues, re-save with UTF-8 (BOM is allowed).
- The import wizards perform a dry run by default. Uncheck `Dry Run` in the wizard to create real records.
- Wizard UI names: "Import Clubs", "Import Teams", "Import Players", "Import Tournament Participants" (available in the module menu).

How to use manually:
- Go to the corresponding import wizard in the Odoo backend (see UI names above).
- Upload the CSV file and click "Parse & Import".
- Inspect the result message for errors and counts.

These CSVs include a few rows that intentionally demonstrate common cases:
- duplicate rows (teams.csv) — to see duplicate detection
- missing required fields (clubs.csv, teams.csv) — to see validation errors
- invalid date (players.csv) — to see date parsing error
- missing references (players.csv, tournament_participants.csv) — to see not-found errors

If you want, I can also add a small script to auto-load these files into the wizards for automated tests or provide sample `base64` encodings used by unit tests.
