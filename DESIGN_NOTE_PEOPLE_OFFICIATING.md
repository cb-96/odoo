# Design Note: People & Officiating Modules

## Module Split Rationale

**Players in sports_federation_people:**
- Tied to club/team master data from sports_federation_base
- Licenses are season-based administrative records
- People concept extends to coaches, staff in future

**Referees in sports_federation_officiating:**
- Operate across tournaments, not within club structure
- Assignments are tournament/match-specific operational concerns
- Certification management is specialized

## License Validity and Eligibility

Licenses support future eligibility checks via:
- Season linkage (season_id)
- Date-based validity (issue_date, expiry_date)
- Status field (only active licenses valid)
- Category field for competition filtering

## Referee Assignment Integration

- federation.match.referee has match_id FK to federation.match
- federation.match has referee_assignment_ids One2many back
- SQL constraint prevents duplicate (match, referee, role)
- Tournament context via related field on assignment

## Extension Points

- Transfer history for players
- Automated eligibility engine
- Referee availability calendar
- Auto-assignment algorithms
- Discipline/suspension records
- Fee payment tracking