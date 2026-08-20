# Auth v1 — Manual de pruebas sin conocimientos técnicos

Este manual permite comprobar el funcionamiento básico de autenticación.

## Antes de empezar

Necesitas:

- La URL del entorno, por ejemplo `https://api.ejemplo.com`.
- Un usuario de prueba entregado por el responsable del sistema.
- Acceso a internet o a la red donde está la API.

No compartas contraseñas, tokens ni capturas que los contengan.

## Prueba de login desde Swagger

Abre en el navegador:

```text
https://TU-URL/docs
```

Reemplaza `TU-URL` por la dirección real de la API.

### 1. Iniciar sesión

1. Busca `POST /api/v1/auth/login`.
2. Pulsa `Try it out`.
3. En `username`, escribe el email del usuario de prueba.
4. En `password`, escribe la contraseña sin compartirla.
5. Pulsa `Execute`.

Resultado esperado:

- Código `200`.
- Aparece `access_token`.
- Aparece `csrf_token`.
- La respuesta establece una cookie de sesión.

Si aparece `401`, revisa que el email y la contraseña sean correctos.

Swagger sirve para comprobar el login y consultar el contrato. Sin embargo,
el navegador gestiona las cookies HttpOnly por detrás y Swagger no es una
herramienta confiable para validar todo el flujo de refresh y logout.
FastAPI documenta esta limitación para las pruebas de cookies desde su
interfaz de documentación.

Para validar refresh y logout usa preferentemente el frontend real. Si no hay
frontend disponible, usa Postman o Insomnia con persistencia de cookies.

### 2. Renovar la sesión desde el frontend o un cliente con cookies

1. Inicia sesión desde el frontend o desde Postman/Insomnia.
2. Conserva el `csrf_token` recibido en el login.
3. Ejecuta `POST /api/v1/auth/refresh` con la cookie guardada y el header
   `X-CSRF-Token`.

Resultado esperado:

- Código `200`.
- Se recibe un nuevo `access_token`.
- Se recibe un nuevo `csrf_token`.

### 3. Cerrar sesión desde el frontend o un cliente con cookies

1. Usa el último `csrf_token` recibido.
2. Ejecuta `POST /api/v1/auth/logout` conservando la cookie de sesión.

Resultado esperado:

- Código `204`.
- La sesión queda cerrada.

## Pruebas de error

Realiza estas pruebas solo con un usuario de prueba:

| Prueba | Resultado esperado |
|---|---|
| Login con contraseña incorrecta | `401` y `AUTHENTICATION_FAILED` |
| Refresh sin cookie | `401` y `REFRESH_FAILED` |
| Refresh con CSRF incorrecto | `403` y `CSRF_INVALID` |
| Datos incompletos | `422` y `VALIDATION_ERROR` |
| Muchas solicitudes seguidas | `429`; esperar el tiempo indicado |

Si aparece `CSRF_INVALID`, no repitas la solicitud indefinidamente. Inicia
nuevamente el login para obtener una sesión y un `csrf_token` nuevos.

## Pruebas adicionales de Auth v1

Estas pruebas requieren los permisos o datos indicados:

| Prueba | Requisito | Resultado esperado |
|---|---|---|
| Registro válido | Usuario `ADMIN` o `SUPERADMIN` | `201` y nunca se muestra la contraseña |
| Registro sin autorización | Usuario sin rol permitido | `403` y `PERMISSION_DENIED` |
| Registro con email repetido | Email ya existente | `409` y `EMAIL_ALREADY_REGISTERED` |
| Registro con negocio repetido | Negocio ya existente | `409` y `BUSINESS_ALREADY_REGISTERED` |
| Verificación válida | Acceso al correo de prueba | `200` |
| Verificación inválida o expirada | Token inválido o usado | `400` y `VERIFICATION_TOKEN_INVALID` |
| Reenvío de verificación | Email de prueba | `202` con respuesta genérica |
| Access token inválido | Token modificado o expirado | `401` y `TOKEN_INVALID` |

Para probar el registro privado, el tester debe usar un access token de un
usuario `ADMIN` o `SUPERADMIN`. Nunca usar cuentas reales de producción.

## Prueba desde el frontend real

Esta prueba es necesaria porque Swagger no comprueba completamente la
configuración del frontend.

1. Abre el frontend en el navegador.
2. Inicia sesión.
3. Navega a una pantalla protegida.
4. Espera o provoca la renovación del access token.
5. Cierra sesión.

Resultado esperado:

- El usuario puede iniciar sesión.
- Las pantallas protegidas cargan correctamente.
- La sesión se renueva sin pedir nuevamente la contraseña.
- El logout termina la sesión.
- El frontend no muestra errores de CORS.

## Cómo informar un fallo

Enviar únicamente:

- Entorno probado: desarrollo, staging o producción.
- Fecha y hora.
- Paso que falló.
- Código HTTP.
- Valor de `code` del error.
- Captura sin contraseñas, cookies ni tokens.

Ejemplo:

```text
Entorno: staging
Paso: refresh
Resultado: 403
Code: CSRF_INVALID
Hora: 2026-08-20 15:30
```

## No se debe probar en v1

Estas funciones no forman parte de Auth v1:

- Recuperación de contraseña.
- MFA obligatorio.
- Login social.
- Revocación automática del access token al cerrar sesión.
- Denylist de access tokens.
- Gestión de dispositivos desde el frontend.
