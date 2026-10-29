-- VM type is scoped to the source SQLite file, never globally unique.
with req as (
    select
      source_file, vm_type_id,
      count(*) as total_observed_vm_requests,
      count(*) filter (where arrived_during_window) as new_vm_requests_in_window,
      count(*) filter (where priority = 0) as high_priority_requests,
      count(*) filter (where is_end_censored) as censored_end_requests,
      percentile_cont(0.5) within group (order by observed_lifetime_days)
        as median_completed_lifetime_days
    from {{ ref('fct_vm_requests') }}
    where vm_type_id is not null
    group by 1,2
),
options as (
    select source_file, vm_type_id,
           count(distinct machine_id) as compatible_machine_ids,
           min(cpu_fraction) as min_normalized_cpu_fraction,
           max(cpu_fraction) as max_normalized_cpu_fraction
    from {{ ref('stg_vm_type_options') }}
    group by 1,2
)
select
    req.source_file, req.vm_type_id,
    req.total_observed_vm_requests, req.new_vm_requests_in_window,
    req.high_priority_requests, req.censored_end_requests,
    req.median_completed_lifetime_days,
    options.compatible_machine_ids,
    options.min_normalized_cpu_fraction,
    options.max_normalized_cpu_fraction
from req
left join options on req.source_file = options.source_file and req.vm_type_id = options.vm_type_id
