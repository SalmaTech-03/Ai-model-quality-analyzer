-- ---------------------------------------------------------
-- PRODUCTION DATA PIPELINE (SNOWFLAKE / BIGQUERY)
-- This query extracts the 'Current' dataset for the dashboard
-- ---------------------------------------------------------

WITH prediction_logs AS (
    SELECT 
        prediction_id,
        model_version,
        prediction_timestamp,
        features, -- JSON variant column
        predicted_value,
        actual_value
    FROM prod_db.ml_logs.housing_model_v1
    WHERE prediction_timestamp >= DATEADD(day, -7, CURRENT_TIMESTAMP())
),

feature_extraction AS (
    SELECT
        prediction_id,
        -- Extract critical features for drift monitoring
        features:MedInc::FLOAT as median_income,
        features:HouseAge::FLOAT as house_age,
        features:AveRooms::FLOAT as avg_rooms,
        predicted_value
    FROM prediction_logs
)

-- Final Export for ModelGuard API
SELECT * FROM feature_extraction;