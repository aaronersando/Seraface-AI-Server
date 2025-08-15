"""
Phase 4 Service: Routine Creation

Creates personalized skincare routines based on recommendations and user preferences.
PRESERVED ORIGINAL LOGIC - Only extracted into service class.
"""

import json
from datetime import datetime
try:
    import google.generativeai as genai
except ImportError:
    print("Warning: google.generativeai not installed. Install with: pip install google-generativeai")
    genai = None
    
from fastapi import HTTPException
from typing import List, Dict, Any
from ..core.config import settings
from ..models.skincare.form_schemas import FormData
from ..models.skincare.analysis_schemas import RoutineStep, SkincareRoutineResponse

# Configure the AI model (same as original)
if genai:
    genai.configure(api_key=settings.GEMINI_API_KEY)


class Phase4Service:
    """Service for Phase 4: Routine Creation (Original logic preserved)"""
    
    def __init__(self):
        if genai:
            self.model = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.model = None

    @staticmethod
    def sanitize_datetime_objects(data: Any) -> Any:
        """
        Recursively convert datetime objects to ISO format strings for JSON serialization.
        Handles nested dictionaries, lists, and datetime objects.
        """
        if isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {key: Phase4Service.sanitize_datetime_objects(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [Phase4Service.sanitize_datetime_objects(item) for item in data]
        elif hasattr(data, 'isoformat'):  # Handle other datetime-like objects
            return data.isoformat()
        else:
            return data

    def get_routine_for_user(self, form_data: FormData, product_recommendations: dict) -> dict:
        """Get routine for user - ORIGINAL LOGIC PRESERVED with datetime sanitization"""
        
        # Sanitize product recommendations to remove datetime objects
        sanitized_recommendations = self.sanitize_datetime_objects(product_recommendations)
        
        user_profile = f"""
    User Profile:
    - Skin Type: {', '.join(form_data.skin_type)}
    - Skin Conditions: {', '.join(form_data.skin_conditions)}
    - Allergies: {', '.join(form_data.allergies)}
    - Product Experiences: {[f"{p.product} ({p.experience})" for p in form_data.product_experiences]}
    - Goals: {', '.join(form_data.goals + ([form_data.custom_goal] if form_data.custom_goal else []))}
    """

        prompt = f"""
    You are a skincare assistant creating a personalized skincare routine for a user.

    User Profile:
    {user_profile}

    Products:
    {json.dumps(sanitized_recommendations, indent=2)}

    Instructions:
    - For each product, create a step-by-step usage instruction.
    - Provide a brief description (e.g., 'Gentle Hydrating Cleanser: Ideal for daily use, removes dirt and impurities').
    - Include days for usage (e.g., 'monday', 'tuesday', 'wednesday', etc.).
    - Specify the time(s) of use in an array (e.g., ["morning", "night"] if it is used twice a day).
    - Provide the duration in seconds (e.g., 30 for cleanser).
    - Provide the waiting time in seconds between products (e.g., 900 for waiting 15 minutes).
    - Only provide the raw JSON without markdown or extra commentary.

    Example:
    "cleanser": {{
        "name": "CeraVe Renewing SA Cleanser",
        "tag": "Gentle Hydrating Cleanser",
        "description": "Ideal for daily use, removes dirt and impurities",
        "instructions": [
            "Wet face with lukewarm water.",
            "Apply a small amount to face and neck.",
            "Massage in circular motions.",
            "Rinse thoroughly."
        ],
        "duration": 30,
        "waiting_time": 900,
        "days": {{
            "monday": true,
            "tuesday": true,
            "wednesday": true,
            "thursday": true,
            "friday": true,
            "saturday": true,
            "sunday": true
        }},
        "time": ["morning"]
    }},
    "moisturizer": {{
        "name": "Neutrogena Hydro Boost Water Gel",
        "tag": "Hyaluronic Acid Moisturizer",
        "description": "Hydrates and replenishes moisture",
        "instructions": [
            "Take a small amount and gently apply to face and neck.",
            "Massage in upward circular motions."
        ],
        "duration": 20,
        "waiting_time": 600,
        "days": {{
            "monday": true,
            "tuesday": true,
            "wednesday": true,
            "thursday": true,
            "friday": true,
            "saturday": true,
            "sunday": true
        }},
        "time": ["morning", "night"]
    }}
    """

        try:
            if not self.model:
                raise HTTPException(status_code=500, detail="AI model not available. Please install google-generativeai package.")
                
            response = self.model.generate_content(prompt)
            raw = getattr(response, 'text', '').strip()

            if raw.startswith("```"):
                raw = raw.strip("`").strip()
                if raw.startswith("json"):
                    raw = raw[4:].strip()

            print("🧪 Raw Response:", raw)

            if not raw:
                raise ValueError("Received an empty response from the AI model.")

            routine = json.loads(raw) 
            return routine

        except Exception as e:
            print("❌ Failed to generate skincare routine:", e)
            raise HTTPException(status_code=500, detail="Failed to create skincare routine")

    def create_routine(self, data: dict) -> Dict[str, Any]:
        """
        Create a personalized skincare routine based on user data and product recommendations.
        ORIGINAL LOGIC PRESERVED with schema validation fix
        """
        try:
            form_data = FormData(**data.get("form_data", {}))
            product_recommendations = data.get("product_recommendations", {})

            if not product_recommendations:
                raise HTTPException(status_code=400, detail="No product recommendations provided")

            routine = self.get_routine_for_user(form_data, product_recommendations)

            # Convert routine dict to list of RoutineStep objects
            routine_list = []
            
            # Handle different AI response formats
            if isinstance(routine, dict):
                # Check if AI returned nested structure with "routine" or "skincare_routine" key
                if "routine" in routine:
                    routine_data = routine["routine"]
                elif "skincare_routine" in routine:
                    routine_data = routine["skincare_routine"]
                else:
                    # Direct format - products are top-level keys
                    routine_data = routine
                
                # Process each product category
                for category, step_data in routine_data.items():
                    if isinstance(step_data, dict):
                        # Make sure all required fields are present for RoutineStep
                        required_fields = ['name', 'tag', 'description', 'instructions', 'duration', 'waiting_time', 'days', 'time']
                        for field in required_fields:
                            if field not in step_data:
                                print(f"⚠️ Missing field {field} in {category}, adding default")
                                if field == 'name':
                                    step_data[field] = f"Step {len(routine_list) + 1}"
                                elif field == 'tag':
                                    step_data[field] = category.replace('_', ' ').title()
                                elif field == 'description':
                                    step_data[field] = f"Apply {category.replace('_', ' ')}"
                                elif field == 'instructions':
                                    step_data[field] = ["Apply as directed"]
                                elif field == 'duration':
                                    step_data[field] = 30
                                elif field == 'waiting_time':
                                    step_data[field] = 300
                                elif field == 'days':
                                    step_data[field] = {
                                        "monday": True, "tuesday": True, "wednesday": True,
                                        "thursday": True, "friday": True, "saturday": True, "sunday": True
                                    }
                                elif field == 'time':
                                    step_data[field] = ["morning"]
                        
                        routine_list.append(step_data)
                        print(f"✅ Added {category} step: {step_data.get('name', 'Unknown')}")
                    else:
                        print(f"⚠️ Invalid step data for {category}: {step_data}")
            else:
                routine_list = routine if isinstance(routine, list) else [routine]

            print(f"✅ Created routine with {len(routine_list)} steps")
            return {
                "product_type": "custom", 
                "routine": routine_list
            }

        except Exception as e:
            print("❌ Error in routine creation:", str(e))
            raise HTTPException(status_code=500, detail=f"Failed to create skincare routine: {str(e)}")

    
phase4_service = Phase4Service()
