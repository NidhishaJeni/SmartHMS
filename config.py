import os


class Config:
    """Base configuration for SmartHMS."""

    SECRET_KEY = os.environ.get("SMARTHMS_SECRET_KEY", "dev-smart-hms-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "SMARTHMS_DATABASE_URI",
        "sqlite:///smart_hms.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # AI / automation
    DIABETES_MODEL_PATH = os.environ.get(
        "SMARTHMS_MODEL_PATH",
        os.path.join(os.path.dirname(__file__), "models", "diabetes_model.pkl"),
    )
    ALERTS_LOG_PATH = os.environ.get(
        "SMARTHMS_ALERTS_LOG_PATH",
        os.path.join(os.path.dirname(__file__), "alerts.log"),
    )


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.environ.get("SMARTHMS_ENV", "development").lower()
    return config_by_name.get(env, DevelopmentConfig)

