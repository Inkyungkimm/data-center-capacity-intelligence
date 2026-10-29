select
    source_file,
    vm_id,
    tenant_id,
    vm_type_id,
    priority,
    priority_label,
    start_day,
    end_day,
    is_end_censored,
    existed_before_observation,
    case
      when end_day is not null and start_day is not null
      then end_day - start_day else null
    end as observed_lifetime_days,
    start_day >= 0 and start_day < 14 as arrived_during_window,
    start_day < 14 and (end_day is null or end_day > 0) as active_in_window
from {{ ref('stg_vm_requests') }}
