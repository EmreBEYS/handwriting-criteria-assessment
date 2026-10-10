import pytest
from app.config import Settings
from pydantic import ValidationError


def production_settings(**overrides) -> dict[str, object]:
    return {
        "_env_file": None,
        "app_env": "production",
        "jwt_secret_key": "a" * 48,
        "require_https": True,
        "object_storage_use_ssl": True,
        "cors_allowed_origins": "https://admin.example.edu",
    } | overrides


def test_secure_production_settings_are_accepted() -> None:
    settings = Settings(**production_settings())

    assert settings.require_https is True
    assert settings.object_storage_use_ssl is True


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"jwt_secret_key": "short"}, "strong production secret"),
        ({"require_https": False}, "HCA_REQUIRE_HTTPS"),
        ({"object_storage_use_ssl": False}, "HCA_OBJECT_STORAGE_USE_SSL"),
        ({"cors_allowed_origins": "http://admin.example.edu"}, "must use HTTPS"),
    ],
)
def test_insecure_production_settings_are_rejected(override, message) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(**production_settings(**override))
