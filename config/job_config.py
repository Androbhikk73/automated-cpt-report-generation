from typing import Optional, Dict, List
from dataclasses import dataclass, field

@dataclass(frozen=True)
class JobConfig:
    name_id: str
    date_stamp_format: str
    scheduled_time: str
    scheduled_type: str
    export_file_mask: str
    export_file_extension: str
    staging_folder_path: str
    destination_file_mask: str
    destination_folder_path: str
    table_id: Optional[str] = None
    app_id: Optional[str] = None
    where_clause: Optional[str] = None
    sort_by: Optional[int] = None
    field_labels: Dict[str, str] = field(default_factory = dict)
    transforms: List[str] = field(default_factory = list)
    header_only_when_empty: bool = True