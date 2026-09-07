# Verification - 2026-09-07

Local command: `.venv/Scripts/python.exe scripts/judge_check.py --live`

Observed output:

```text
35 passed in 10.97s
4 passing (4 mocha)
deletion_gate=PASSED verdict=MEMORY_REQUIRED
writer_complete=true
database_file_bytes=393216
separate_process_recall=PASSED
memory_access_disabled=PASSED verdict=MEMORY_REQUIRED
judge_check=PASSED
```

Live verification began at 2026-09-07T09:22:28 UTC. Writer PID 40840 exited
before reader PID 36136 opened the persisted database. The reader recalled two
observations and returned BLOCK_REPEAT_DEPLOYER. The fixed clean risk input is
a controlled demonstration input, not a separately verified token safety result.

SQLite file size: 393216 bytes (384 KiB). This is file size, not a measurement
of the SDK's internal 5 MB quota accounting.

Public Railway health and all three proof endpoints passed this session.
The revised local UI was also exercised through the browser: live history and
recall, existing Base receipt verification, and isolated unavailable-memory test.
Receipt verification is read-only; no new transaction or paid x402 call was made.

## Still required before submission

- Publish and verify the final UI deployment.
- Record and upload a real 2-5 minute demo with an uninterrupted fresh-process
  recall segment, visible UTC time or commit, and the Base evidence anchor.
- Publish two required posts and retain their public URLs.
- Fill the registered build form and mark it ready after checking all links.
- Optional: ask Rohan for genuine feedback and consent to link it publicly.
  No external pilot, payment, or endorsement is established by this report.

Draft submission fields and the unsent pilot invitation: SUBMISSION-PACK.md.
