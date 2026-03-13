"""
Mock tools used by the LangGraph Swarm agents.

These simulate external integrations (email, SMS, analytics) and
return structured results for agent consumption.
"""

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

# ---------------------------------------------------------------------------
# Load ML Models Once at Module Import
# ---------------------------------------------------------------------------
_MODELS_DIR = Path(__file__).parent / "models"
_ML_MODEL = None
_TFIDF_VECTORIZER = None
_MODEL_COLUMNS = None

try:
    _ML_MODEL = joblib.load(_MODELS_DIR / "viral_classifier_model.joblib")
    _TFIDF_VECTORIZER = joblib.load(_MODELS_DIR / "tfidf_vectorizer.joblib")
    _MODEL_COLUMNS = joblib.load(_MODELS_DIR / "model_columns.joblib")
    print("[ML Tool] Successfully loaded viral prediction models.")
except Exception as e:
    print(f"[ML Tool] Warning: Could not load ML models: {e}")
    # Models remain None; predict_best_posting_times will handle gracefully


def send_bulk_email(
    event_id: int,
    recipients: list[str],
    subject: str,
    body: str,
) -> dict[str, Any]:
    """
    Mock bulk email sender.

    In production, this would integrate with SendGrid, SES, etc.

    Args:
        event_id: The tenant event identifier.
        recipients: List of recipient email addresses.
        subject: Email subject line.
        body: Email body content.

    Returns:
        A dict with delivery status and count.
    """
    return {
        "status": "sent",
        "event_id": event_id,
        "recipients_count": len(recipients),
        "subject": subject,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": f"[MOCK] Bulk email sent to {len(recipients)} recipients for event {event_id}.",
    }


def send_emergency_sms(
    event_id: int,
    recipients: list[str],
    message: str,
) -> dict[str, Any]:
    """
    Mock emergency SMS/notification sender.

    In production, this would integrate with Twilio, SNS, etc.

    Args:
        event_id: The tenant event identifier.
        recipients: List of phone numbers or contact identifiers.
        message: The emergency alert message.

    Returns:
        A dict with alert dispatch status.
    """
    return {
        "status": "dispatched",
        "event_id": event_id,
        "recipients_count": len(recipients),
        "alert_message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": f"[MOCK] Emergency SMS dispatched to {len(recipients)} officials for event {event_id}.",
    }


def predict_posting_times(
    event_name: str,
    target_audience: str = "general",
) -> dict[str, Any]:
    """
    Mock social-media posting-time predictor.

    Simulates an analytics engine that recommends optimal posting
    windows for maximum engagement.

    Args:
        event_name: Name of the event for context.
        target_audience: Audience segment to optimize for.

    Returns:
        A dict with recommended posting windows.
    """
    # Simulated optimal time slots
    recommended_slots = [
        {"day": "Monday", "time": "09:00 AM", "platform": "LinkedIn", "expected_reach": random.randint(500, 5000)},
        {"day": "Wednesday", "time": "12:30 PM", "platform": "Twitter/X", "expected_reach": random.randint(1000, 8000)},
        {"day": "Friday", "time": "06:00 PM", "platform": "Instagram", "expected_reach": random.randint(2000, 10000)},
        {"day": "Saturday", "time": "10:00 AM", "platform": "Facebook", "expected_reach": random.randint(800, 6000)},
    ]

    return {
        "event_name": event_name,
        "target_audience": target_audience,
        "recommended_posting_slots": recommended_slots,
        "analysis_note": f"[MOCK] Optimal posting times computed for '{event_name}' targeting '{target_audience}' audience.",
    }


# ---------------------------------------------------------------------------
# ML-Powered Posting Time Prediction (returns both text & hourly data)
# ---------------------------------------------------------------------------

def predict_best_posting_times(
    llm_text: str,
    llm_platform: str,
    llm_sentiment: str,
    llm_day_of_week: int,
    llm_hashtag_count: int,
) -> tuple[str, dict[str, Any]]:
    """
    Predict the best hour(s) of the day to post content based on a pre-trained
    Random Forest model. Returns both formatted text AND hourly engagement data.

    Args:
        llm_text: The promotional post text to analyze.
        llm_platform: Social media platform (e.g., "twitter", "linkedin", "instagram").
        llm_sentiment: Sentiment group (must match training data).
        llm_day_of_week: Integer 0-6 representing day of week (0=Monday, 6=Sunday).
        llm_hashtag_count: Number of hashtags in the post.

    Returns:
        Tuple of (formatted_string, hourly_data_dict):
        - formatted_string: Human-readable text with best posting times
        - hourly_data_dict: Dict with 'hours' list containing engagement tier for each hour 0-23
    """
    # Check if models are loaded
    if _ML_MODEL is None or _TFIDF_VECTORIZER is None or _MODEL_COLUMNS is None:
        error_msg = "❌ ML models not available. Cannot predict posting times."
        return error_msg, {
            "hours": [
                {"hour": h, "engagement": "Unknown", "engagement_score": 0.0}
                for h in range(24)
            ]
        }

    try:
        # Calculate text statistics
        text_length = len(llm_text)
        word_count = len(llm_text.split())

        # Normalize platform
        llm_platform = llm_platform.lower().strip()

        # Create hourly test data for all 24 hours
        hourly_tests = []
        for hour in range(24):
            hourly_tests.append({
                'Hour': hour,
                'DayOfWeek': llm_day_of_week,
                'Platform': llm_platform,
                'Sentiment_Group': llm_sentiment,
                'Text_Length': text_length,
                'Word_Count': word_count,
                'Hashtag_Count': llm_hashtag_count,
                'Text': llm_text
            })

        df_test = pd.DataFrame(hourly_tests)

        # Apply TF-IDF transformation on text
        text_features = _TFIDF_VECTORIZER.transform(df_test['Text']).toarray()
        text_df = pd.DataFrame(text_features, columns=_TFIDF_VECTORIZER.get_feature_names_out())

        # Encode categorical variables (Platform, Sentiment_Group)
        base_features = df_test.drop('Text', axis=1)
        X_encoded = pd.get_dummies(base_features, columns=['Platform', 'Sentiment_Group'])

        # CRITICAL: Reindex to match training columns (fills missing with 0)
        non_text_columns = [col for col in _MODEL_COLUMNS if col not in text_df.columns]
        X_encoded = X_encoded.reindex(columns=non_text_columns, fill_value=0)

        # Combine base features + TF-IDF features
        X_final = pd.concat([X_encoded.reset_index(drop=True), text_df.reset_index(drop=True)], axis=1)

        # Ensure column order matches training
        X_final = X_final[_MODEL_COLUMNS]

        # Predict class probabilities for all 24 hours
        probabilities = _ML_MODEL.predict_proba(X_final)
        model_classes = [str(c) for c in _ML_MODEL.classes_]

        # Expected-value weights for engagement classes
        class_weights = {
            "Low": 1,
            "Medium": 2,
            "High": 3,
            "Viral": 4,
        }

        # Build hourly data structure for bar chart
        hourly_data = []
        viral_hours = []
        high_hours = []

        for hour, probs in enumerate(probabilities):
            # Dominant class (argmax)
            dominant_idx = max(range(len(probs)), key=lambda idx: probs[idx])
            tier = model_classes[dominant_idx]

            # Expected-value engagement score from class probabilities
            engagement_score = sum(
                float(prob) * float(class_weights.get(label, 0))
                for prob, label in zip(probs, model_classes)
            )

            hourly_data.append({
                "hour": hour,
                "engagement": tier,
                "engagement_score": round(engagement_score, 2),
            })
            if tier == 'Viral':
                viral_hours.append(f"{hour:02d}:00")
            elif tier == 'High':
                high_hours.append(f"{hour:02d}:00")

        # Format the result for UI
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_name = day_names[llm_day_of_week] if 0 <= llm_day_of_week <= 6 else f"Day {llm_day_of_week}"

        result_lines = [
            f"📊 ML-Powered Posting Time Prediction",
            f"Platform: {llm_platform.title()} | Day: {day_name} | Sentiment: {llm_sentiment}",
            ""
        ]

        if viral_hours:
            result_lines.append(f"🔥 VIRAL Hours: {', '.join(viral_hours)}")
        if high_hours:
            result_lines.append(f"📈 HIGH Engagement Hours: {', '.join(high_hours)}")

        if not viral_hours and not high_hours:
            result_lines.append("⚠️  No 'High' or 'Viral' engagement predicted for this content.")
            result_lines.append("💡 Tip: Try adjusting the sentiment, adding more hashtags, or revising the text.")

        formatted_result = "\n".join(result_lines)
        
        return formatted_result, {"hours": hourly_data}

    except Exception as e:
        error_msg = f"❌ Error during ML prediction: {str(e)}"
        return error_msg, {
            "hours": [
                {"hour": h, "engagement": "Unknown", "engagement_score": 0.0}
                for h in range(24)
            ]
        }

