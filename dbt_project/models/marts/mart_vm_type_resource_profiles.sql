-- Grain: each source file + VM type + machine identifier.
-- Fractions are *not* comparable to absolute cores or electricity demand.
select
    source_file,
    vm_type_id,
    machine_id,
    count(*) as available_option_rows,
    min(cpu_fraction) as min_normalized_cpu_fraction,
    max(cpu_fraction) as max_normalized_cpu_fraction,
    avg(cpu_fraction) as avg_normalized_cpu_fraction,
    avg(memory_fraction) as avg_normalized_memory_fraction,
    avg(ssd_fraction) as avg_normalized_ssd_fraction,
    avg(nic_fraction) as avg_normalized_nic_fraction
from {{ ref('stg_vm_type_options') }}
group by 1,2,3
