# Contrato de autenticación v1

Estado: AUTH v1 CERRADO — contrato congelado para avanzar al siguiente dominio  
Fecha de referencia: 2026-08-20

La versión 1 de Auth queda dada de alta a nivel de código y contrato. El
frontend puede implementar este contrato sin esperar las mejoras futuras.
Las tareas de staging y QA quedan como validación operativa, no como cambios
del contrato v1.

Este documento es la referencia técnica y funcional del dominio `auth`. Toda
modificación futura debe conservar este contrato. La regla principal es que el
frontend que implemente v1 no tenga que cambiar su integración para consumir la
versión definitiva.

## Filosofía de compatibilidad

- No eliminar ni renombrar endpoints existentes.
- No cambiar nombres de campos de request o response.
- No cambiar silenciosamente los códigos HTTP actuales.
- Los nuevos campos deben ser opcionales o únicamente de respuesta.
- Los códigos de error son parte del contrato; los mensajes no lo son.
- Las mejoras internas de seguridad deben ser transparentes para el frontend.
- Las funcionalidades que requieran una pantalla nueva deben agregarse como
  endpoints nuevos y opcionales.
- No se hará obligatoria una funcionalidad que fuerce a rediseñar el flujo v1.

## Alcance de v1

### Incluido

- Registro privado para `ADMIN` y `SUPERADMIN`.
- Login local con email y contraseña.
- Access token JWT Bearer.
- Refresh token opaco almacenado en cookie HttpOnly.
- Rotación de refresh tokens.
- Detección de reutilización de refresh tokens.
- Logout mediante revocación del refresh token actual.
- Protección CSRF para refresh y logout.
- Verificación y reenvío de correo electrónico.
- Autorización por roles, permisos y tenant.
- Rate limiting de operaciones de autenticación.

### Excluido deliberadamente

- Recuperación de contraseña.
- MFA o segundo factor obligatorio.
- Login social.
- Revocación automática del access token al cerrar sesión.
- Denylist de access tokens.
- Gestión de dispositivos desde el frontend.

## Endpoints estables

La API pública está bajo `/api/v1` y el router de autenticación bajo `/auth`.

### Registro privado

`POST /api/v1/auth/register`

Requiere access token y rol `ADMIN` o `SUPERADMIN`.

El body mantiene los dos objetos definidos por los schemas actuales:

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

Respuesta exitosa: `201` con `UserResponse`. Nunca incluye `password` ni
`password_hash`.

### Verificación de correo

`GET /api/v1/auth/verify-email?token=<token>`

Respuesta exitosa: `200`.

### Reenvío de verificación

`POST /api/v1/auth/resend-verification`

Body:

```json
{
  "email": "usuario@example.com"
}
```

Respuesta exitosa: `202`. La respuesta es genérica para no revelar si el
correo existe.

### Login

`POST /api/v1/auth/login`

Content-Type: `application/x-www-form-urlencoded`.

Campos:

- `username`: email del usuario, porque OAuth2 exige ese nombre de campo.
- `password`: contraseña.

Respuesta exitosa: `200`.

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "csrf_token": "<csrf-token>"
}
```

Además, el backend establece la cookie HttpOnly `refresh_token`.

### Refresh

`POST /api/v1/auth/refresh`

- No recibe el refresh token en el body.
- El navegador envía automáticamente la cookie.
- El frontend debe enviar `X-CSRF-Token`.
- El frontend debe usar `credentials: "include"`.

Respuesta exitosa: `200` con el mismo formato de login. El frontend debe
reemplazar el `csrf_token` anterior por el nuevo.

### Logout

`POST /api/v1/auth/logout`

- Usa la cookie de refresh.
- Requiere `X-CSRF-Token` cuando existe una sesión.
- Usa `credentials: "include"`.

Respuesta exitosa: `204`.

## Contrato de tokens

- El access token se envía en `Authorization: Bearer <access_token>`.
- El frontend no debe leer, almacenar ni enviar manualmente el
  `refresh_token`.
- El backend rota el refresh token en cada refresh exitoso.
- El frontend debe impedir refresh concurrentes. Dos refresh simultáneos con
  el mismo token pueden activar la detección de reutilización y revocar la
  familia de sesión.
- Logout revoca el refresh token, pero el access token ya emitido continúa
  válido hasta su expiración.
- El backend puede rechazar un access token antes de su expiración si el
  usuario está eliminado, inactivo, suspendido, bloqueado o sin acceso al
  negocio. Esto es una validación del estado actual del usuario, no una
  revocación automática del JWT.

## Contrato global de errores

Todos los errores deben terminar con esta estructura:

```json
{
  "status": "fail",
  "code": "ERROR_CODE",
  "message": "Mensaje visible para el usuario.",
  "details": {}
}
```

### Errores controlados

- `status`: `fail`.
- `code`: identificador técnico estable.
- `message`: texto visible; no debe ser usado como identificador por el
  frontend.
- `details`: objeto JSON, vacío cuando no hay datos adicionales.

### Errores de validación

```json
{
  "status": "fail",
  "code": "VALIDATION_ERROR",
  "message": "Los datos enviados no son válidos.",
  "details": {
    "password": "La contraseña debe contener al menos una letra mayúscula"
  }
}
```

Los `ValueError` lanzados dentro de validators de Pydantic se conservan en
`details`.

### Errores internos

En producción:

```json
{
  "status": "error",
  "code": "INTERNAL_ERROR",
  "message": "Ocurrió un error interno.",
  "details": {}
}
```

Los detalles técnicos y stack traces se guardan en logs internos. El entorno
de desarrollo actualmente puede mostrar el stack para depuración.

### Códigos públicos implementados en Auth v1

La estructura y los códigos públicos ya están implementados. Las llamadas que
no envían un código continúan funcionando con `APP_ERROR` por compatibilidad.
El catálogo estable de Auth v1 es:

- `AUTHENTICATION_FAILED`
- `PERMISSION_DENIED`
- `TOKEN_REQUIRED`
- `TOKEN_INVALID`
- `CSRF_INVALID`
- `REFRESH_FAILED`
- `EMAIL_ALREADY_REGISTERED`
- `BUSINESS_ALREADY_REGISTERED`
- `VERIFICATION_TOKEN_INVALID`
- `RESOURCE_NOT_FOUND`
- `CONFLICT`
- `VALIDATION_ERROR`
- `INTERNAL_ERROR`

Los códigos representan acciones que el frontend puede tomar. No se crea un
código por cada excepción interna; las causas detalladas se conservan en logs
internos.

`REFRESH_FAILED` y `AUTHENTICATION_FAILED` agrupan causas que producen la
misma acción del frontend. Por ejemplo, un refresh expirado, inválido o
reutilizado requiere iniciar sesión nuevamente; la razón específica no debe
exponerse como contrato público.

## Checklist de cierre de Auth v1

- [x] `AppException` acepta `code` y `details` opcionales.
- [x] Las llamadas existentes no se rompen si no envían `code`.
- [x] El código por defecto es `APP_ERROR`.
- [x] El manejador global devuelve `status`, `code`, `message` y `details`.
- [x] Los errores de validación usan `VALIDATION_ERROR`.
- [x] Los errores internos usan `INTERNAL_ERROR`.
- [x] Asignar los códigos del catálogo a las excepciones concretas de auth.
- [x] El catálogo público evita códigos por causa interna.
- [x] Publicar y revisar el OpenAPI generado con el frontend.
- [ ] Verificar CORS, `AUTH_FRONTEND_URL` y cookies en staging (QA operativo,
  no cambia el contrato).
- [x] Actualizar las pruebas antiguas para este contrato.
- [x] Ejecutar la suite de pruebas en un entorno con dependencias instaladas.

Estado de pruebas locales: `28 passed`. Las pruebas unitarias y de contrato no
requieren MongoDB ni Redis. La validación de integración con esos servicios
debe ejecutarse en staging o CI cuando estén disponibles.

## Cierre y siguiente dominio

Auth v1 se considera cerrado para desarrollo de nuevos dominios porque:

- Los endpoints y sus formatos de request/response están definidos.
- El contrato global de errores está definido y versionado.
- El flujo de cookies, CSRF, refresh y logout está definido.
- Los códigos HTTP y códigos públicos de error están documentados.
- El frontend puede integrar login, refresh, logout y registro privado.
- Las mejoras posteriores no requieren modificar la integración existente.

El siguiente dominio puede desarrollarse utilizando las dependencias de Auth
ya existentes. No debe modificar silenciosamente este contrato. Cualquier
mejora futura de Auth debe agregarse como una extensión compatible, un endpoint
nuevo o una nueva versión de API.

### Pendientes posteriores a v1

Estas tareas no bloquean el inicio del siguiente dominio:

- Ejecutar las pruebas manuales de QA en staging.
- Confirmar CORS, `AUTH_FRONTEND_URL`, cookies seguras y `credentials`.
- Verificar que staging use una base de datos y Redis separados de producción.
- Revisar logs y métricas en el entorno desplegado.
- Implementar posteriormente las mejoras listadas en la sección de evolución.

### Guía rápida para el frontend

La documentación interactiva está disponible en `/docs` durante desarrollo y
el contrato JSON en `/openapi.json`. El frontend debe usar los códigos de error
de la propiedad `code`, nunca los textos de `message`.

- Para `login`, enviar `username` con el email y `password` como
  `application/x-www-form-urlencoded`.
- Para `refresh` y `logout`, usar `credentials: "include"` y no leer ni enviar
  manualmente `refresh_token`; es una cookie HttpOnly.
- Enviar `X-CSRF-Token` en `refresh` y `logout` cuando exista una sesión.
- Después de un refresh exitoso, reemplazar el `csrf_token` almacenado en
  memoria por el nuevo valor recibido.
- Ante `AUTHENTICATION_FAILED`, `TOKEN_INVALID` o `REFRESH_FAILED`, iniciar
  nuevamente el flujo de login.
- Ante `PERMISSION_DENIED`, mostrar acceso denegado sin reintentar login.
- Ante `VALIDATION_ERROR`, mostrar los datos de `details` junto al campo
  correspondiente.
- Ante `429`, respetar el header `Retry-After` antes de reintentar.
- Ante `500` o `503`, mostrar un error temporal y no interpretar detalles
  técnicos.

## Evolución hacia la versión definitiva

Las siguientes mejoras deben realizarse sin cambiar este contrato:

- Validación adicional de claims JWT.
- Rotación y versionado de claves.
- Auditoría y monitoreo.
- Mejoras de rate limiting.
- Cabeceras de seguridad.
- Revocación interna de tokens.
- Optimización del almacenamiento de sesiones.

Si en el futuro se incorpora MFA, recuperación de contraseña o login social,
deben agregarse como flujos nuevos. No se debe cambiar silenciosamente el
login v1 para exigir pasos que el frontend actual no conoce.
