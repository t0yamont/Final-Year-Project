# Source audit and authority record

Audit date: 27 October 2026 (Europe/London). Status: initial documentary audit; no data collection, training, university submission or approval occurred.

## Authority and scope

The user's request authorises starting the project through multiple agents, recording actions, discoveries and problems in dissertation-transferable form, and leaving compute-heavy jobs to the student. The supplied guide is project context. Its embedded Codex prompts are proposed task descriptions, not separate user instructions or proof that any stage has been completed. Course requirements are recorded as claims of the supplied course documents; current deadlines and approval status still require the university record.

The named Markdown guide is the initial planning baseline, subject to the user's subsequent request to use every useful FastF1 season rather than fixing data scope to 2025. Deadlines, ethics details and weekly hours remain pending at the user's direction. An adjacent document, `F1 energy deployment.docx`, describes three research questions and prioritises SAC as an optional comparison. The named guide instead describes four questions, including mixed-session data and observable profile ablations. These plans must not be silently combined. The guide's source C4, `F1_Energy_Deployment_Workplan.docx`, was not present in the inspected directory. The differently named DOCX has not been assumed to be that updated version.

## Local source register

All paths below are relative to the inspected source folder: `C:\Users\monti\OneDrive\Área de Trabalho\UNI\Year 3\Professional Project`.

| ID | File | Bytes | SHA-256 | Audit status |
| --- | --- | ---: | --- | --- |
| C1 | COM3001 marking formNGD2026.docx | 2206908 | 497c634332e50a05effccc375b56df5b21f71bf502512442c7b538d64657f314 | Paragraphs and marking tables extracted |
| C2 | COM3001lectures.pdf | 394238 | 5cf68da9e54167fd445bba117a84d5a6222d6464451c7d197a942c2ae3964fa2 | 22 PDF pages; relevant sections extracted |
| C3 | What gets a high marks.html | 3570 | ec169c4049e5c3e0b9beffdc3bc141c2e39b35b0db267ac2b737e0942b94b53e | Local HTML read |
| P1 | F1_COM3001_Step_by_Step_Guide.md | 60213 | fbd6b83de2e02deb619dee421326ff5ab50fb7da30011e0afea7ef23d67184d2 | Current supplied planning guide |
| P2 | F1 energy deployment.docx | 54777 | f2c08fc4fc556d6c5b34c0cc8259f2413e5c8f0144053a241d3039374571e89c | Paragraph text inspected for scope comparison |

C2's title page identifies the Department of Computer Science, September 2026, with a revision history entry dated 25 September 2026. A filename alone was not used as edition evidence. DOCX page numbers have not been verified by rendering; C1 locators below use the actual section headings instead. This audit addresses content, not document layout fidelity.

## Verified course requirements

| Claim | Source locator | Implication for this project |
| --- | --- | --- |
| Approximately 450 hours including report preparation; regular supervisor meetings at least fortnightly | C2 section 1.4, PDF page 6 | Record actual student hours separately from automated execution; schedule meetings with supervisor |
| Projects require ethical approval | C2 section 1.6.3, PDF page 7 | Record evidence through the university process; public data does not constitute approval |
| Supervisor must verify ethics evidence by a January deadline; otherwise LSEP receives 0% | C1 paragraph immediately preceding the LSEP heading | Exact day and required process remain unknown |
| Important dates are on SurreyLearn | C2 section 2.1, PDF page 9 | Do not convert the guide's proposed calendar into official deadlines |
| Synopsis at least three pages, references excluded; introduction, literature, technical overview and workplan | C2 section 4.1, PDF page 13 | Prepare an evidence-based synopsis after scope and initial technical checks |
| Interim discussion approximately 20 minutes | C2 section 4.2, PDF page 13 | Practise explaining assumptions and the implementation |
| Draft report includes current report and planned contents | C2 section 4.3, PDF page 14 | Keep chapter outline alongside drafted content |
| Final PDF below 20 MiB; video at most five minutes and below 500 MiB, playable in VLC; software archive below 500 MiB | C2 section 4.4, PDF page 14 | Verify real final file sizes; these are submission constraints, not outputs already produced |
| Body at most 50 pages, at least 11-point font; single spacing recommended | C2 section 7.2, PDF page 20 | Keep evidence appendices separate from the main argument |
| Chapters start on new pages; captions below figures and tables; numbered sections, figures, tables and important equations | C2 section 7.4, PDF page 21 | Apply at final typesetting, preserving stable evidence IDs now |
| Reference style discussed with supervisor; Harvard and IEEE are standard departmental options | C2 section 7.3, PDF page 21 | Use stable BibTeX keys now; final style remains to confirm |
| AI use described within relevant chapters, plus a reflection chapter | C1 AI-use section | Record assistance and verification; student supplies personal reflection |
| LSEP must relate project to UN SDGs | C1 LSEP section | Make a reasoned connection without claiming measured environmental benefit |

C1 confirms weights of 20% context, 30% methodology/implementation, 20% evaluation, 10% LSEP, 10% presentation/video, 5% AI use and 5% project management. C3 explains that a thoroughly investigated poor-performing method can support a strong project when obvious flaws are addressed and conclusions are justified. Its phrase about 450 credits conflicts with C2's 45 credits and approximately 450 hours; use C2 for workload planning.

## Technical reading coverage

The literature matrix records four entries: PPO, FastF1's channel documentation in source, a statistical-evaluation paper, and a qualifying energy-control paper. PPO sections 2-6 and the evaluation paper sections 2-4 were inspected from accessible full text; this is a targeted first reading, not a completed critical review. FastF1's `Telemetry` class was inspected directly. The qualifying paper's institutional metadata and abstract were available; its full text was not inspected, so detailed modelling and numerical claims remain unset.

Technical sources were accessed on 27 October 2026. The FastF1 branch URL is mutable and not a release lock. Archive the exact installed version and commit before implementation relies on it. Neither source availability nor a public repository establishes permission to redistribute F1 telemetry.

## Actions, discoveries and problems

Actions: inspected the source inventory; extracted C1 with `python-docx` and relevant C2 pages with `pypdf`; read C3 and guide text; calculated SHA-256 checksums; opened primary technical sources; created a critical-reading matrix, bibliography, bounded related-work draft and report outline.

Discoveries: supplied course requirements support continuous writing and transparent AI use; the exact ethics deadline remains external; project-plan variants differ; public source-channel documentation is suitable evidence for a measurement boundary, not an assertion of audited dataset coverage.

Problems: a first console extraction failed after encountering character encoding limitations. A second extraction used JSON with ASCII escaping and completed successfully. FastF1's documentation endpoint returned 403; official raw source was used. The qualifying paper DOI failed in the browsing tool; an institutional record supplied metadata and abstract only. The evaluation PDF exceeded the browsing tool's content limit; the versioned arXiv HTML full text was used. These are retrieval limitations, not evidence that papers or data do not exist.

No source document was modified. No legal conclusion, ethics approval, independent experimental result or student learning experience is asserted here.

## Next evidence to obtain

1. Official SurreyLearn dates, ethics status/evidence, and current university AI guidance.
2. Supervisor confirmation of the current four-question scope and reference style.
3. Full text for Salazar and colleagues (2019), then a comparison of states, constraints, information access and terminal conditions.
4. A primary source on structural identifiability/system identification; no such literature has yet been critically reviewed here.
5. Applicable FIA regulation issue and data-use conditions, before assigning regulatory limits or redistributing data.

## Multi-season acquisition addendum

A later user instruction expands the data ambition to every season that is useful. Operational API source was therefore inspected on 27 October 2026. This does not imply that any session has been downloaded by the source-review agent.

The [official event API source](https://raw.githubusercontent.com/theOehrly/Fast-F1/master/fastf1/events.py) documents timing support from 2018 onward. Earlier historical schedules/results are not equivalent to telemetry. Its current schedule exposes session names/dates and `F1ApiSupport`; installed-version inspection is necessary because older releases differ. The initial candidate metadata range is therefore 2018 through 2026, excluding future sessions at retrieval time and recording unavailable years explicitly.

The [official cache source](https://raw.githubusercontent.com/theOehrly/Fast-F1/master/fastf1/req.py) currently uses `Cache.configure(cache_dir=...)`; `enable_cache` is deprecated from 3.9. It documents HTTP and parsed-data caching and built-in rate limiting. Current source also describes authenticated live-timing requests, so any access requirement must be handled through the supported account flow, without recording credentials in project files.

A one-lap export can still require loading a session's telemetry. Plan disk and request budgets from measured pilot use, retain failures and access denials, and expand sequentially only after the pilot is audited. These are project acquisition decisions. API documentation establishes an interface, not achieved completeness.

Cross-season inclusion requires compatibility checks. The official [2020 Sakhir announcement](https://www.formula1.com/en/latest/article/f1-to-use-bahrains-high-speed-outer-track-for-sakhir-grand-prix.6niLbb2btc0IrscR1BMpx8) distinguishes Bahrain's outer and standard layouts. Consequently, country or venue name is insufficient as a layout key. [FIA's 2026 overview](https://www.fia.com/news/f1s-new-era-everything-you-need-know-about-how-fia-making-formula-1-more-competitive-more) describes a redesigned power unit, and its [2026 refinement notice](https://www.fia.com/news/refinements-2026-fia-formula-1-regulations-agreed-all-stakeholders) illustrates changing energy provisions. These notices justify separating regimes; they do not establish the exact regulation issue applicable to a selected session.

Proposed catalogue fields therefore include season, event, session, exact layout identifier, team/car context, regulation issue/status, source version and retrieval outcome. Useful historical coverage should be preserved even where observations cannot enter a common vehicle fit. A matched-era primary analysis and explicitly labelled cross-era sensitivity analysis are possible designs, to be chosen after the coverage audit. No year has yet been certified compatible by this review.
