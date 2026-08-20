# Rate limits de Auth por entorno

Este documento define los valores recomendados para los límites de solicitudes
del dominio `auth` en cada entorno.

## Regla principal

Los nombres de las variables son siempre los mismos. Lo que cambia es su valor
según el entorno donde se ejecuta la aplicación.

No se deben colocar los tres bloques juntos en un mismo archivo `.env`.

## Desarrollo local

Usar en el `.env` local del desarrollador:

```env
ENVIRONMENT=development

RATE_LIMIT_REGISTER_PER_HOUR=50
RATE_LIMIT_VERIFY_PER_MINUTE=100
RATE_LIMIT_RESEND_PER_HOUR=30
RATE_LIMIT_LOGIN_PER_MINUTE=100
RATE_LIMIT_REFRESH_PER_MINUTE=100
RATE_LIMIT_LOGOUT_PER_MINUTE=100
```

Estos valores facilitan las pruebas manuales sin desactivar completamente la
protección contra abusos.

## Staging o QA

Usar en el servidor destinado a pruebas del frontend y QA:

```env
ENVIRONMENT=staging

RATE_LIMIT_REGISTER_PER_HOUR=50
RATE_LIMIT_VERIFY_PER_MINUTE=100
RATE_LIMIT_RESEND_PER_HOUR=30
RATE_LIMIT_LOGIN_PER_MINUTE=100
RATE_LIMIT_REFRESH_PER_MINUTE=100
RATE_LIMIT_LOGOUT_PER_MINUTE=100
```

Staging debe utilizar una base de datos y un Redis separados de producción.

## Producción

Configurar estas variables directamente en el servidor o plataforma de
despliegue:

```env
ENVIRONMENT=production

RATE_LIMIT_REGISTER_PER_HOUR=5
RATE_LIMIT_VERIFY_PER_MINUTE=10
RATE_LIMIT_RESEND_PER_HOUR=3
RATE_LIMIT_LOGIN_PER_MINUTE=10
RATE_LIMIT_REFRESH_PER_MINUTE=10
RATE_LIMIT_LOGOUT_PER_MINUTE=10
```

## Notas operativas

- El código de las rutas no cambia entre entornos.
- La aplicación lee el valor al iniciar; después de modificarlo hay que
  reiniciar la aplicación.
- El tester debe usar la URL de staging, nunca la URL de producción.
- No subir archivos `.env` ni contraseñas al repositorio.
- Si staging y producción usan Redis, deben tener instancias o namespaces
  separados para no compartir contadores de rate limit.
- Las variables definidas directamente en el servidor tienen prioridad sobre
  las variables del archivo `.env`.
