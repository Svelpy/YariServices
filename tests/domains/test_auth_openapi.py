from app.main import app


def test_auth_openapi_documents_v1_contract():
    schema = app.openapi()
    paths = schema["paths"]

    expected_paths = {
        "/api/v1/auth/register",
        "/api/v1/auth/verify-email",
        "/api/v1/auth/resend-verification",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/logout",
    }

    assert expected_paths <= paths.keys()
    assert "ErrorResponse" in schema["components"]["schemas"]

    login = paths["/api/v1/auth/login"]["post"]
    assert "application/x-www-form-urlencoded" in login["requestBody"]["content"]
    assert {"200", "401", "422", "429", "500", "503"} <= login["responses"].keys()
    assert "Set-Cookie" in login["responses"]["200"]["headers"]

    refresh = paths["/api/v1/auth/refresh"]["post"]
    assert any(parameter["in"] == "cookie" for parameter in refresh["parameters"])
    assert any(parameter["name"] == "X-CSRF-Token" for parameter in refresh["parameters"])

    logout = paths["/api/v1/auth/logout"]["post"]
    assert "204" in logout["responses"]
    assert "Set-Cookie" in logout["responses"]["204"]["headers"]


def test_register_openapi_documents_private_roles():
    operation = app.openapi()["paths"]["/api/v1/auth/register"]["post"]

    assert "ADMIN" in operation["description"]
    assert "SUPERADMIN" in operation["description"]
