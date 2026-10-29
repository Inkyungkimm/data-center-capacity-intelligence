select *
from {{ ref('mart_daily_capacity_demand') }}
where new_vm_requests < 0
   or vms_overlapping_day < new_vm_requests
   or day_index < 0
   or day_index > 13
