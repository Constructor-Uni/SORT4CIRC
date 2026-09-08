# Example exchange API

The checked-in [OpenAPI document](../spec/openapi/dpp-api-v1.json) describes the /v1 exchange routes. The profile and implementation version is 2.0.0; the route prefix is an independently versioned API major.

The API supports passport creation and retrieval, carrier binding and resolution, appending lifecycle events and material observations, validation and digest verification. Query views and role/organisation scopes select the permitted projection. The access matrix in spec/access-matrix.json is the public-profile policy.

Synthetic example. Not SORT4CIRC project data.

The worked example shows exact request payloads and routes with an in-process client. DemoAuth accepts X-DPP-Role and X-DPP-Organisation headers. These headers are fictional identity assertions, not credentials. The default PublicOnlyAuth rejects claimed roles and permits only public access.

Write idempotency keys are scoped to caller, organisation, role, operation and resource. A repeated key with changed content returns a conflict. Conditional writes use the ETag/If-Match behaviour tested by the API suite.

Local worker processing is a Python operation. It is excluded from the public exchange contract. Health returns status and the public schema version only.
