select
    source_file,
    option_id,
    vm_type_id,
    machine_id,
    cpu_fraction,
    memory_fraction,
    hdd_fraction,
    ssd_fraction,
    nic_fraction,
    ingested_at
from {{ source('azure', 'vm_type_options') }}
