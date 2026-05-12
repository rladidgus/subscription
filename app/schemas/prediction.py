from pydantic import BaseModel, Field


class CutoffPredictionRequest(BaseModel):
    apartment_name: str
    region_code: str
    general_supply_units: int = Field(ge=0)
    sale_price: float = Field(ge=0)
    competition_rate: float = Field(ge=0)
    housing_price_index: float = Field(ge=0)
    supply_year: int
    supply_quarter: int = Field(ge=1, le=4)
    area_m2: float = Field(ge=0)


class CutoffPredictionResponse(BaseModel):
    apartment_name: str
    predicted_cutoff_score: float
    model_name: str
    confidence_note: str
