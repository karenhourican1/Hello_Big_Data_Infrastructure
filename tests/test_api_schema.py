from schemathesis.specs.openapi.loaders import from_asgi

from bdi_api.app import app

app.openapi_version = "3.0.2"  # Required since schemathesis thinks it can't support 3.1


# Use property base testing of the entire API using schemathesis
schema = from_asgi("/openapi.json", app)


@schema.parametrize()
def test_property_base(case) -> None:
    pass
    # response = case.call_asgi()
    # case.validate_response(response)
