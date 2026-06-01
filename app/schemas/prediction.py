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


class ApplyHomeCandidateFilter(BaseModel):
    apartment_name: str | None = None
    house_manage_no: str | None = None
    pblanc_no: str | None = None
    model_no: str | None = None
    house_type: str | None = None
    reside_secd: str | None = None
    subscription_rank_code: str | None = None


class ApplyHomePredictionRequest(ApplyHomeCandidateFilter):
    limit: int = Field(default=10, ge=1, le=100)


class ApplyHomePredictionResult(BaseModel):
    apartment_name: str
    house_manage_no: str
    pblanc_no: str
    model_no: str
    house_type: str
    region_code: str
    announcement_date: str | None = None
    reside_secd: str
    subscription_rank_code: str
    predicted_cutoff_score: float
    actual_cutoff_score: float | None = None
    model_name: str
    confidence_note: str


class ApplyHomePredictionResponse(BaseModel):
    results: list[ApplyHomePredictionResult]


class ApplyHomeClassificationRequest(BaseModel):
    user_score: float = Field(ge=0, le=84)
    margin: float = Field(default=5, ge=0, le=20)
    candidates: list[ApplyHomeCandidateFilter] = []
    apartment_name: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class ApplyHomeClassifiedResult(ApplyHomePredictionResult):
    user_score: float
    score_gap: float
    category: str
    category_label: str


class ApplyHomeClassificationResponse(BaseModel):
    available_now: list[ApplyHomeClassifiedResult]
    prepare_later: list[ApplyHomeClassifiedResult]
    difficult: list[ApplyHomeClassifiedResult]
