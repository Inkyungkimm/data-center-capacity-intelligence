# Data dictionary

## Microsoft Azure public data source

Official documentation: <https://github.com/Azure/AzurePublicDataset/blob/master/AzureTracesForPacking2020.md>

`raw.vm_requests` has a grain of one VM request ID *per original source SQLite file*.

| Column | Meaning |
|---|---|
| `source_file` | Original SQLite member filename; protects source-scoped ID uniqueness |
| `vm_id` | Source's anonymized VM request ID |
| `tenant_id` | Anonymized tenant ID within source file |
| `vm_type_id` | Requested type ID within source file |
| `priority` | 0=high; 1=low (low-priority requests can be evicted) |
| `start_day` | Relative fractional day; may be negative |
| `end_day` | Relative fractional day; NULL means censored |
| `ingested_at` | Local ingestion timestamp; not an Azure event timestamp |

`raw.vm_type_options` has a grain of VM option row ID per original source SQLite file.

| Column | Meaning |
|---|---|
| `source_file` / `option_id` | Original scope and row identity |
| `vm_type_id`, `machine_id` | Valid type and machine combination within source file |
| `cpu_fraction`, `memory_fraction`, `hdd_fraction`, `ssd_fraction`, `nic_fraction` | Normalized resource requirement relative to a specific machine generation (not absolute facility metrics) |

## Observed window and censoring

- Observation spans days `[0, 14)`.
- Requests started before day 0 remain relevant for demand overlap.
- End times after day 14 are *not* cut off in the raw data, and an absent end is a censored outcome.
- A VM that overlaps any part of a day contributes one to `vms_overlapping_day`; this count is not a peak simultaneous VM count.
- Cross-file identifiers must never be joined without the `source_file` key.
