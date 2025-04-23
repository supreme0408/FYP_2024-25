from pydantic import BaseModel, Field

class WeatherAnalysisInsights(BaseModel):
    Analysis_of_Rainfall_Trends: str = Field(description="Paragraph of text of Monthly averages, surplus/deficit periods, effects on irrigation and soil moisture.")
    Analysis_of_Temperature: str = Field(description="Paragraph of text Seasonal fluctuations, frost risks, heatwave trends, impact on crop cycles.")
    Crop_Suitability_and_Crop_Growth_Requirements: str = Field(description="Paragraph of text Recommended crops based on rainfall and temperature patterns. Ideal conditions for the recommended crops — temperature range, rainfall needs, soil conditions.")
    Predictive_Insights_of_weather: str = Field(description="Paragraph of text Challenges like monsoon delays, drought risks, or heat stress, and strategies to mitigate them.")