import os
from typing import List
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Access variables
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")

# Initialize the OpenAI client
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# Define Pydantic models for structured responses
class Nutrients(BaseModel):
    Nitrogen: str
    Phosphorus: str
    Potassium: str

class SoilInfo(BaseModel):
    location: str
    soil_type: str
    pH: float
    moisture_content: str
    organic_matter: str
    nutrients: Nutrients

class CropInfo(BaseModel):
    crop_name: str
    optimal_soil_type: str
    pH_range: str
    water_requirements: str
    nutrient_requirements: str
    growing_season: str

class Disease(BaseModel):
    name: str
    symptoms: str
    causes: str
    prevention: str
    treatment: str

class CropDiseaseInfo(BaseModel):
    crop_name: str
    diseases: List[Disease]

class SoilCropCompatibility(BaseModel):
    crop_name: str
    location: str
    compatibility: str
    reasoning: str

# Define the service class with static methods
class AgriInfoService:
    @staticmethod
    def get_soil_info(location: str) -> SoilInfo:
        completion = client.beta.chat.completions.parse(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": "Extract structured soil information from the input."},
                {"role": "user", "content": f"Provide the soil type and detailed soil properties including pH, moisture content, organic matter, and nutrient levels for {location}."},
            ],
            response_format=SoilInfo,
        )
        return completion.choices[0].message.parsed

    @staticmethod
    def get_crop_info(crop_name: str) -> CropInfo:
        completion = client.beta.chat.completions.parse(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": "Extract structured crop information from the input."},
                {"role": "user", "content": f"Provide detailed information for the crop {crop_name}, including optimal soil type, pH range, water requirements, nutrient requirements, and growing season."},
            ],
            response_format=CropInfo,
        )
        return completion.choices[0].message.parsed

    @staticmethod
    def get_crop_disease_info(crop_name: str, location: str) -> CropDiseaseInfo:
        completion = client.beta.chat.completions.parse(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": "Extract structured crop disease information from the input."},
                {"role": "user", "content": f"List common diseases affecting {crop_name} in {location}, including symptoms, causes, prevention, and treatment."},
            ],
            response_format=CropDiseaseInfo,
        )
        return completion.choices[0].message.parsed

    @staticmethod
    def get_soil_crop_compatibility(crop_name: str, location: str) -> SoilCropCompatibility:
        completion = client.beta.chat.completions.parse(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": "Assess soil-crop compatibility from the input."},
                {"role": "user", "content": f"Evaluate the compatibility of growing {crop_name} in {location}, including reasoning."},
            ],
            response_format=SoilCropCompatibility,
        )
        return completion.choices[0].message.parsed

# Example usage:
if __name__ == "__main__":
    location = "Gadchiroli, India"
    crop = "Rice"

    soil_data = AgriInfoService.get_soil_info(location)
    print("Soil Information:")
    print(soil_data)

    crop_data = AgriInfoService.get_crop_info(crop)
    print("\nCrop Information:")
    print(crop_data)

    disease_data = AgriInfoService.get_crop_disease_info(crop, location)
    print("\nCrop Disease Information:")
    print(disease_data)

    compatibility_data = AgriInfoService.get_soil_crop_compatibility(crop, location)
    print("\nSoil-Crop Compatibility:")
    print(compatibility_data)
