# FastF1 archive access diagnosis — 28 October 2026

## Outcome
The Bahrain pilot is blocked by missing authenticated access to essential timing-archive metadata, rather than absence of all telemetry. A working schedule audit does not test this access path.

## Local evidence
The installed FastF1 version is 3.9.0. Three small unauthenticated requests to the exact pilot path returned HTTP 401 with zero-byte bodies: SessionInfo.jsonStream, DriverList.jsonStream and SessionStatus.jsonStream, beneath https://livetiming.formula1.com/static/2025/2025-04-13_Bahrain_Grand_Prix/2025-04-12_Qualifying/ . No credential or account access was attempted.

The original pilot cache contains parsed timing, timing-app, track-status, car and position data. It lacks the three metadata responses. A copy was placed at work/diagnostic/cache; offline loading against the copy reproduced the failure without changing original results. Detailed evidence is in work/diagnostic/offline-load.log. SessionStatus fails first, leaving session_start_time unavailable. FastF1 core.py then needs this value while processing PitOutTime in _load_laps_data (around line 1477), so lap construction fails. FastF1 logger.py catches the internal exception and only logs a warning at normal verbosity; the later session.laps access raises the less informative DataNotLoadedError.

## Supported repair
The upstream maintainer reports archive authentication is now required and identifies F1 TV Access or a higher tier as necessary. FastF1 3.9 supports authentication. See the maintainer's October 18 comments in [issue 978](https://github.com/theOehrly/Fast-F1/issues/978). The linked [authentication documentation](https://docs.fastf1.dev/versions/dev/api_reference/accounts_auth.html) was not accessible through the web reader; instructions below were verified against the installed 3.9.0 CLI source instead.

The user can run these commands in an interactive PowerShell terminal in this project folder:

```powershell
.\.venv\Scripts\python.exe -m fastf1 auth f1tv --authenticate --method password
.\.venv\Scripts\python.exe -m fastf1 auth f1tv --status
```

The first command prompts locally for the F1 account email and password, and FastF1 stores its authentication token. Enter credentials only in that local prompt, not in this chat, source code, shell command arguments or research artifacts. The second prints token validity and subscription status without displaying the token. No authentication command was executed during diagnosis. The installed CLI also offers a browser method; its local source describes an additional browser addon, so the native interactive method is the simpler supported path here.

After successful authentication with a suitable account, rerun the pilot to a new output directory. Preserve the original failed result and compare the new logs and lap count. Do not clear the original cache, fabricate session start time, copy someone else's authentication token, or treat Jolpica results as replacement telemetry. Successful account authentication alone is not proof the requested archived session loads; that must be checked by the new pilot. If eligible access is unavailable, continue synthetic simulator validation while empirical acquisition remains blocked.

## Runtime check
The project's .venv currently has no torch module installed. CUDA availability in PyTorch therefore could not be assessed; this does not establish that the machine lacks a CUDA-capable GPU. Installation and hardware validation are separate work.

## Work record
Action: inspected installed FastF1 code and pilot cache; reproduced the failure offline using a cache copy; issued three bounded metadata probes; checked the upstream issue; read supported CLI options. Discovery: a partially populated cache can coexist with an authentication-blocked lap constructor. Problem: empirical pilot needs user account authentication. No full telemetry download, model training, login or credential inspection occurred in this diagnosis. No project modules or original results were modified.
