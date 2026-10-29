-- Grain: observation day (0..13) x priority (0/1). Active = overlaps day,
-- not instantaneous concurrency. Includes pre-existing VMs with negative starts.
with days as (
    select generate_series(0, 13)::integer as day_index
),
priorities as (
    select 0 as priority, 'high' as priority_label
    union all select 1 as priority, 'low' as priority_label
),
base as (
    select days.day_index, priorities.priority, priorities.priority_label,
           f.vm_id, f.source_file, f.start_day, f.end_day
    from days cross join priorities
    left join {{ ref('fct_vm_requests') }} f
      on f.priority = priorities.priority
     and f.start_day < (days.day_index + 1)
     and (f.end_day is null or f.end_day > days.day_index)
)
select
    day_index,
    priority,
    priority_label,
    count(vm_id) as vms_overlapping_day,
    count(vm_id) filter (where start_day >= day_index and start_day < day_index + 1)
      as new_vm_requests
from base
group by day_index, priority, priority_label
