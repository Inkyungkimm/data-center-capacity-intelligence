-- Each requested VM type should have at least one resource profile in the same source file.
select distinct r.source_file, r.vm_type_id
from {{ ref('stg_vm_requests') }} r
left join {{ ref('stg_vm_type_options') }} t
  on r.source_file = t.source_file and r.vm_type_id = t.vm_type_id
where r.vm_type_id is not null and t.vm_type_id is null
