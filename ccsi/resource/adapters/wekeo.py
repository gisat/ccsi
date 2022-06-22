from pydantic import BaseModel, Field, root_validator
from typing import List, Optional

from ccsi.resource.adapters import AdapterABC
from ccsi.resource.parameters import ResourceParametersABC

class BoundingBoxValues:
    pass

class Wekeohrvpp(AdapterABC):
    datasetId: Optional[str]
    boundingBoxValues: Optional[List[dict]]
    dateRangeSelectValues: Optional[List[dict]]
    stringChoiceValues: Optional[List[dict]]
    stringInputValues: Optional[List[dict]]

    @root_validator(pre=True)
    def set_values(cls, values):
        definitions = values.pop('definition')
        for parameter, values in values.items():
            pass
        return values




