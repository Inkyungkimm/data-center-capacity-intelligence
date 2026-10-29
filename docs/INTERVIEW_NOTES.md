# Engineering and domain talking points

## Technical trade-offs

1. **Correct identifier grain:** Azure documentation says IDs are file-specific, so the ingestion primary key is `(source_file, vm_id)` rather than `vm_id`.
2. **Censored intervals:** `NULL` end time is *not* zero lifetime; means the VM was still alive beyond the release window/cap.
3. **Already-running workload:** Negative start times describe pre-existing VMs. They count toward daily overlap, not new demand.
4. **Data quality:** SQL constraints, dbt schema tests, and custom tests catch duplicate rows, invalid priority values, missing keys, bad time sequences, and unresolved VM type references.
5. **Idempotent pipeline:** PostgreSQL upserts keep repeated imports from doubling totals.
6. **A truthful metric:** The daily overlap is the number of VMs whose life interval intersects a day, *not* instantaneous concurrency or physical power capacity. It is useful for trend monitoring but not precise peak sizing.
7. **Workload to physical infrastructure:** VM trace data inform server resource demand. Translating CPU and memory reservations to facility IT load requires server performance/power curves, utilization, redundancy, cooling, and PUE. Those inputs are absent, so no MW estimates are produced.

## Example interview explanation

> I was interested in how structured resource-demand information supports data-center capacity planning. I built a reproducible analytics stack using Microsoft's public Azure allocation traces, PostgreSQL, and dbt. The tricky parts were source-scoped identifiers, censored VM end times, and defining metrics correctly. I implemented staging and mart models, quality tests and a dashboard. I deliberately avoided presenting normalized CPU resource fractions as electrical power, because the source doesn't support that inference.

## Honest scope

- The project is a *workload analytics* portfolio project.
- It is **not** evidence of deployment to a real facility, energy management system, or live Azure account.
- Do not put a processed VM count on a resume until the actual real dataset is ingested.
