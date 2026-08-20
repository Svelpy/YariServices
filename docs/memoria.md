# Memoria de pendientes

## Dominio Business

### 1. Negocios inactivos en el acceso público por slug

`GET /businesses/slug/{slug}` es una ruta pública utilizada por el comprador.

El servicio actualmente filtra:

```python
{
    "slug": slug,
    "is_deleted": False,
}
```

Pendiente: revisar si también debe incluir:

```python
"is_active": True
```

La decisión esperada es que un negocio inactivo no sea visible públicamente.

### 2. Repetir la revisión en otros módulos

Auditar todas las rutas públicas que consulten documentos por `slug`, dominio,
barcode u otro identificador público.

Verificar que sus servicios filtren correctamente:

- `is_deleted=False`.
- `is_active=True`, cuando el modelo tenga este campo.
- Solo los campos permitidos para exposición pública.

No asumir que todos los módulos deben aplicar exactamente el mismo filtro;
confirmar el comportamiento esperado de cada dominio.

### 3. Consistencia del propietario al crear un negocio

`create_business()` verifica que el usuario no sea ya propietario de otro
negocio mediante `Business.owner_id`, pero se debe revisar también si el
usuario ya tiene un `business_id` asignado.

Pendiente: impedir que la creación sobrescriba el tenant actual del usuario y
deje inconsistente la relación entre:

- `Business.owner_id`.
- `User.business_id`.

### 4. Atomicidad de la creación

La creación realiza dos operaciones:

1. Crear el documento `Business`.
2. Actualizar el `User` propietario.

Pendiente: evaluar una transacción de MongoDB o una estrategia de compensación
para evitar un negocio creado sin usuario vinculado si la segunda operación
falla.

### 5. Decidir el permiso de borrado lógico para `ADMIN`

Revisar si el rol `ADMIN` debe poder ejecutar el borrado lógico (`soft delete`)
de un negocio.

Separar claramente las decisiones:

- `SUPERADMIN`: puede realizar borrado físico (`hard delete`).
- `ADMIN`: confirmar si puede realizar borrado lógico.
- Restauración de un negocio eliminado, si será necesaria.
- Auditoría mediante `deleted_by`, `deleted_at` y `updated_by`.

Si se otorga el permiso a `ADMIN`, actualizar de forma coordinada:

- `ROLE_PERMISSIONS`.
- La dependencia de la ruta `DELETE /businesses/{business_id}`.
- La lógica del servicio.
- Los tests de permisos y auditoría.

## Estado de tests

Última ejecución del dominio Business:

```text
38 passed
274 warnings
```

Los warnings corresponden a deprecaciones de dependencias y no a fallos del
código del dominio.
