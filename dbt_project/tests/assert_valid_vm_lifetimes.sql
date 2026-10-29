-- Any row returned is a failing assertion. Null end time is censored and valid.
select source_file, vm_id, start_day, end_day
from {{ ref('stg_vm_requests') }}
where start_day is null
   or (end_day is not null and end_day < start_day)
