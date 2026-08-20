# Auth v1 — Guía para frontend

## Referencias

- Base URL de desarrollo: `http://localhost:8000`
- Swagger: `{BASE_URL}/docs`
- OpenAPI JSON: `{BASE_URL}/openapi.json`
- Rutas de auth: `{BASE_URL}/api/v1/auth`

Reemplaza `{BASE_URL}` por la URL del entorno correspondiente.

## Reglas importantes

- El frontend debe usar `code` para decidir qué hacer. No debe interpretar
  `message` como identificador.
- El `refresh_token` es una cookie `HttpOnly`; el frontend no debe leerlo,
  guardarlo ni enviarlo manualmente.
- Las llamadas de `refresh` y `logout` deben usar `credentials: "include"`.
- El `csrf_token` se guarda únicamente en memoria y se reemplaza después de
  cada refresh exitoso.
- El access token se envía como `Authorization: Bearer <access_token>`.
- Logout revoca el refresh token, pero el access token continúa válido hasta
  su expiración.
- Swagger sirve para consultar el contrato, pero el flujo real de refresh y
  logout debe validarse desde el frontend porque depende de cookies HttpOnly.

## Login

Endpoint: `POST /api/v1/auth/login`

Content-Type: `application/x-www-form-urlencoded`.

Campos obligatorios:

- `username`: email del usuario.
- `password`: contraseña.

Ejemplo:

```javascript
const response = await fetch(`${BASE_URL}/api/v1/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  credentials: "include",
  body: new URLSearchParams({
    username: email,
    password,
  }),
});

const data = await response.json();
// Guardar access_token y csrf_token en memoria.
```

Respuesta exitosa `200`:

```json
{
  "access_token": "<jwt>",
  "csrf_token": "<csrf-token>",
  "token_type": "bearer"
}
```

El backend establece automáticamente la cookie `refresh_token`.

## Refresh

Endpoint: `POST /api/v1/auth/refresh`

```javascript
const response = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
  method: "POST",
  headers: { "X-CSRF-Token": csrfToken },
  credentials: "include",
});

const data = await response.json();
// Reemplazar access_token y csrf_token en memoria.
```

No enviar `refresh_token` en el body ni en un header propio.

## Logout

Endpoint: `POST /api/v1/auth/logout`

```javascript
await fetch(`${BASE_URL}/api/v1/auth/logout`, {
  method: "POST",
  headers: { "X-CSRF-Token": csrfToken },
  credentials: "include",
});
```

Respuesta exitosa: `204 No Content`.

Después del logout, eliminar de memoria el access token y el `csrf_token`.

## Registro privado

Endpoint: `POST /api/v1/auth/register`

Requiere access token con rol `ADMIN` o `SUPERADMIN`.

Body JSON:

```json
{
  "user": {
    "email": "usuario@example.com",
    "password": "Passw0rd123"
  },
  "business": {
    "name": "Mi negocio"
  }
}
```

Respuesta exitosa: `201`. La respuesta nunca contiene `password` ni
`password_hash`.

## Verificación y reenvío de correo

Verificación: `GET /api/v1/auth/verify-email?token=<token>`

Reenvío: `POST /api/v1/auth/resend-verification`

```json
{
  "email": "usuario@example.com"
}
```

La respuesta del reenvío es genérica para no revelar si el email existe.

## Contrato de errores

Todos los errores tienen esta forma:

```json
{
  "status": "fail",
  "code": "ERROR_CODE",
  "message": "Texto visible",
  "details": {}
}
```

Códigos principales:

| Código | Acción del frontend |
|---|---|
| `AUTHENTICATION_FAILED` | Mostrar error de autenticación o iniciar login |
| `TOKEN_REQUIRED` | Solicitar autenticación |
| `TOKEN_INVALID` | Eliminar access token e iniciar login |
| `REFRESH_FAILED` | Eliminar sesión local e iniciar login |
| `CSRF_INVALID` | Invalidar la sesión local e iniciar login nuevamente; no reintentar indefinidamente |
| `PERMISSION_DENIED` | Mostrar acceso denegado; no repetir login |
| `VALIDATION_ERROR` | Mostrar los campos incluidos en `details` |
| `EMAIL_ALREADY_REGISTERED` | Informar que el email ya está registrado |
| `BUSINESS_ALREADY_REGISTERED` | Solicitar otro nombre de negocio |
| `VERIFICATION_TOKEN_INVALID` | Informar que el enlace de verificación ya no es válido |
| `CONFLICT` | Informar conflicto sin usar el texto de `message` como ID |

Para `429`, respetar el header `Retry-After`. Para `500` y `503`, mostrar un
mensaje temporal y no mostrar detalles técnicos.

## Checklist del frontend

- [ ] Login usa formulario URL-encoded.
- [ ] Login, refresh y logout usan `credentials: "include"`.
- [ ] Nunca se lee `document.cookie` para obtener `refresh_token`.
- [ ] El access token se envía como Bearer.
- [ ] El `csrf_token` se mantiene en memoria y se reemplaza tras refresh.
- [ ] Solo existe un refresh simultáneo; se evita doble refresh concurrente.
- [ ] Los errores se procesan por `code`.
- [ ] `message` no se usa como identificador.
- [ ] La contraseña no se imprime en logs ni se guarda en localStorage.
