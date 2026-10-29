select
    source_file,
    vm_id,
    tenant_id,
    vm_type_id,
    priority,
    case when priority = 0 then 'high' when priority = 1 then 'low' else 'unknown' end as priority_label,
    start_day,
    end_day,
    end_day is null as is_end_censored,
    (start_day < 0) as existed_before_observation,
    ingested_at
from {{ source('azure', 'vm_requests') }}
