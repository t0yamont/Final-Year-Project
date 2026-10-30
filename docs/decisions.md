# Decision register

Date convention: Europe/London. Initial entries: 27 October 2026. A proposed decision is not supervisor approval. Append later reversals with their evidence; retain superseded entries.

| ID | Status | Decision | Alternative considered | Rationale and consequence | Evidence or next check |
| --- | --- | --- | --- | --- | --- |
| D001 | Adopted for setup | Separate observed telemetry, reconstructed quantities and optimised simulation outputs | Treat inferred actions as measured labels | The inverse problem can admit multiple explanations; every artifact needs an evidence-class label | Supplied guide, Scientific boundary and Step 09; verify source schema during audit |
| D002 | Superseded in data scope by D010; reporting candidates remain provisional | Initially use 2025 as the candidate season and Bahrain as the candidate reporting circuit | Select another season or circuit immediately | Follow the guide's starting position without asserting usable data or regulatory compliance | One-event audit and archived rules must precede final choice |
| D003 | Proposed | Use retrospective known-circuit held-out-session evaluation | Pre-qualifying timestamp-cutoff prediction or unseen-track transfer | Mixed-session research may use later data; a retrospective label avoids a false forecasting claim | Freeze complete session IDs after audit; supervisor discussion pending |
| D004 | Adopted for initial design | Begin with one reference vehicle and deployment-only action; omit harvesting | Full hybrid model or silent pooling of different cars | Keeps the core inverse and control studies explainable; results remain model-conditional | Justify parameters and test sensitivity before controller claims |
| D005 | Adopted for evaluation plan | Compare PPO with refined DP and uniform/tuned heuristics using common physics | Use only a weak fixed heuristic | Distinguishes value of learning from baseline and discretisation effects | Independent tiny exhaustive reference and DP convergence required |
| D006 | User requirement | Student runs model training and other heavy computation manually | Assistant launches training or season-wide processing | User explicitly reserved heavy usage for manual execution | Every handoff needs runnable commands; expected outputs; measured pilot cost and recovery checks |
| D007 | Adopted for documentation | Keep dated actions, discoveries, problems, evidence and limitations in Markdown and CSV | Write only a retrospective final narrative | Records transfer into dissertation methods and discussion while preserving provenance | Scope and evidence matrix created; source review and test evidence linked by coordinator |
| D008 | Adopted for uncertainty | Leave unknown dates, approval status and parameter values unset | Infer plausible deadlines or numerical vehicle values | Unverified specifics would create false evidence | Student supplies official dates and ethics record; source work supplies justified ranges |
| D009 | Scope priority | Implement profile conditioning after a verified core; defer SAC, regeneration and transfer | Run every extension in parallel | Core validity and fair comparisons take priority within the academic workload | Revisit once runtime and simulator gates are known |

## Initial action, discovery and problem record

**Action:** recorded research choices and their alternatives before data fitting. **Discovery:** the guide's suggested PPO run sizes are planning ranges, not execution instructions from the student. **Problem:** source review, hardware, academic dates and supervisor preference are still being established. No experimental result or ethics approval is implied by adoption of a planning decision.

## Follow-up decisions — 27 October 2026

| ID | Status | Decision | Alternative considered | Rationale and consequence | Evidence or next check |
| --- | --- | --- | --- | --- | --- |
| D010 | User requirement; supersedes D002 data scope | Pull from FastF1 and audit every season that can usefully contribute | Restrict acquisition planning to 2025 | Broadens source coverage; require per-season availability, quality, layout and technical-regime gates | Student clarification during setup; bounded API metadata audit by coordinator |
| D011 | Adopted compatibility safeguard | Keep incompatible vehicle/regulatory regimes and layout versions separate; require a separately justified 2026 model | Pool all historical telemetry into one reference model | More data does not imply interchangeable physics; stratify, condition or exclude with reasons | Record each included season's role before fitting; source limits still require verification |
| D012 | User requirement | Keep deadlines, ethics and weekly hours pending | Repeatedly block independent work for these details | Student explicitly requested pending status; preserve unresolved institutional requirements | No dates or approvals inferred; revisit when student supplies evidence |
| D013 | Provisional source reconciliation | Use guide's four RQs as the current planning baseline without claiming supervisor agreement | Treat older three-question document as final agreement | Source documents differ in scope; named C4 workplan was not found | Supervisor/student review remains pending; retain both document histories |
## Repository continuation — 27 October 2026

**Action:** cloned the user-supplied GitHub repository and inspected the existing foundation. Added the `audit-schedules` CLI command, optional FastF1 dependency range, metadata catalogue, provenance manifest and offline tests. Added manual pilot and multi-season instructions in `data_audit.md`.

**Discovery:** the repository already has an analytic fixture and extensive research scope/source records. Schedule enumeration is the next missing acquisition stage. The official FastF1 events interface accepts an explicit backend and testing inclusion; missing support must remain unknown rather than converting NaN to true.

**Decision:** retain the existing package and CLI; supersede the separate local starter script. Include testing sessions in the catalogue; separate their later retrieval from normal race-event session lookup. Pin the schedule backend and retain failures. Reject existing output directories to preserve evidence.

**Problems:** normal Git transport failed locally with a Windows credential-provider error; using Git's OpenSSL backend for this clone succeeded without disabling certificate verification. The original course documents and guide are referenced in the source register but absent from this repository. No live FastF1 request was executed and the optional dependency range remains unverified.

**Validation:** all 13 offline tests passed, including the inherited 10 foundation tests. No data-coverage, simulator-calibration or model-performance conclusion follows from those tests.

**Next step:** manually run the one-season metadata pilot, inspect failures and source versions, then expand to candidate seasons. Prepare the bounded telemetry audit after metadata review. Model training and bulk collection remain with the student.
