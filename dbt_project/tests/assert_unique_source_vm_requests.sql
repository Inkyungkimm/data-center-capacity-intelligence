select source_file, vm_id, count(*) as n
from {{ ref('fct_vm_requests') }}
group by 1,2 having count(*) > 1
