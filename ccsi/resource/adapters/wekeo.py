from pydantic import BaseModel, Field, root_validator, validator
from typing import List, Optional

from ccsi.resource.adapters import AdapterABC
from ccsi.resource.parameters import ResourceParametersABC



class BoundingBoxValues(BaseModel):
    name: str
    bbox: List[float]

    @validator('bbox', pre=True)
    def set_bbox(cls,  value):
        return list(map(float, value.split(',')))

    def dict(self)-> List[dict]:
        return [{"name": self.name, "bbox": self.bbox}]


class WekeoMultipleChoice(BaseModel):
    items: List[dict] = Field(default_factory=list)

    def dict(self):
        serialized = [item for item in self.items if not None in item.values()]
        if serialized:
            return serialized
        else:
            return None


class WekeoHRVPP(AdapterABC):
    datasetId: Optional[str]
    boundingBoxValues: Optional[List[dict]]
    dateRangeSelectValues: Optional[List[dict]]
    stringChoiceValues: Optional[List[dict]]
    stringInputValues: Optional[List[dict]]
    query_params: dict

    @root_validator(pre=True)
    def set_values(cls, values):
        definitions = values.pop('definition')
        transformed = {k: v for parameter, value in values.items() for k, v in
                       definitions.get_parameter(parameter).transform(value).items()}

        boundingBoxValues = BoundingBoxValues(name='bbox', bbox=transformed.get('bbox'))

        dateRangeSelectValues = WekeoMultipleChoice()
        dateRangeSelectValues.items.append({'name': 'temporal_interval',
                                            'start': transformed.get('start'),
                                            'end': transformed.get('end')})

        stringChoiceValues = WekeoMultipleChoice()
        stringChoiceValues.items.append({'name': 'productType', 'value': transformed.get('productType').get('type')})
        stringChoiceValues.items.append({'name': 'platformSerialIdentifier', 'value': transformed.get('platformSerialIdentifier')})

        stringInputValues = WekeoMultipleChoice()
        stringInputValues.items.append({'name': 'uid', 'value': transformed.get('uid')})
        stringInputValues.items.append({'name': 'tileId', 'value': transformed.get('tileId')})
        stringInputValues.items.append({'name': 'name', 'value': transformed.get('name')})
        stringInputValues.items.append({'name': 'productVersion', 'value': transformed.get('productVersion')})

        return {'datasetId': transformed.get('productType').get('dataset'),
                'boundingBoxValues': boundingBoxValues.dict(),
                'dateRangeSelectValues': dateRangeSelectValues.dict(),
                'stringChoiceValues': stringChoiceValues.dict(),
                'stringInputValues': stringInputValues.dict(),
                'query_params': {'size': transformed.get('size'),
                                 'page': transformed.get('page')}}


