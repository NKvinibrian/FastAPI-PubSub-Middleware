from dataclasses import dataclass
from app.domain.entities.integrations.integration import IntegrationWithAuthEntity
from typing import Optional, List


@dataclass
class SetupEntity(IntegrationWithAuthEntity):
    module_name: str
    industrial_code: Optional[List[str]]
