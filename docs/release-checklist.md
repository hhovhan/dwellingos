# Release checklist

## Required artifacts

- [x] `output/rules.json`
- [x] `output/lookups.json` covering 500 addresses
- [x] `output/changes.json` covering T1–T5
- [x] `output/reference_case_report.json` with 20 source-anchored regression cases
- [x] Public-repository-ready source and README
- [x] Live-demo-ready static interface
- [x] Demo video script
- [x] Technical video script
- [x] Team video script
- [x] State-by-state source review
- [x] One-page method note
- [x] Legal review packet with unresolved-source triage and sign-off fields
- [x] Zero unsupported extraction candidates
- [x] Desktop browser verification with no console errors
- [x] 390px mobile verification with no horizontal overflow
- [x] Static-host deployment configuration
- [ ] Public GitHub URL
- [x] Public deployment URL: https://dwelling.hovhannes.dev/
- [ ] Recorded and uploaded videos
- [ ] Team member accounts attached on Hack-Nation
- [ ] Submission completed on Hack-Nation and the backup Google form

## Final human checks

- Replace team placeholders with real names and contributions.
- Confirm the organizer’s exact deadline. Hack-Nation stated three approximately one-minute videos: team, demo and teach/technical.
- Verify every public URL in an incognito window.
- Run `npm run pipeline` from a clean checkout.
- Do not claim production legal accuracy or legal advice.

## Verified local release

- 57 rules and 5,419 evaluations
- 47 automated tests, 9 extraction/11 address holdout checks, and 20 non-attorney reference cases passing
- Census address-range check: 383 single matches; 117 unresolved or ambiguous. Parcel-level municipal boundaries remain unverified.
- Local operator workbench imports a `DEMO-` property and previews new-source impact; static deployment does not host these operations.
- All 500 properties have six category summaries
- T1–T5 affected sets: 250, 90, 140, 110 and 0
- `npm run pipeline` and `npm run release:check` pass
