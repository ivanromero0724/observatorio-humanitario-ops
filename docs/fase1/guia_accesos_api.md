# Guía para habilitar las APIs — Observatorio Humanitario OPS

**Fecha de consulta:** 05/11/2026. **Objetivo:** permitir que las extracciones del proyecto utilicen credenciales autorizadas sin compartirlas por chat ni incorporarlas a commits.

## 1. HDX HAPI (OCHA) — prioridad 1

Portal: https://hapi.humdata.org/docs

1. Abrir documentación interactiva y localizar **encode_identifier**.
2. Introducir nombre `observatorio-humanitario-ops` y un correo institucional autorizado; generar el identificador.
3. En GitHub, abrir **Settings → Secrets and variables → Actions → New repository secret**.
4. Crear secreto `HDX_APP_IDENTIFIER`, con el identificador generado.
5. El workflow `.github/workflows/fase1_cobertura.yml` **ya lo lee** como variable de entorno. Ejecutar GitHub Actions → Fase 1 - Verificar cobertura de fuentes → Run workflow, o solicitar una revisión técnica del script.

Documentación oficial: https://hdx-hapi.readthedocs.io/en/latest/getting-started/

## 2. OIM DTM API V3 — prioridad 1

Portal: https://dtm-apim-portal.iom.int/

1. Registrar cuenta institucional; APIs → API-V3 → Subscribe.
2. Tras la activación, buscar **Primary key** en Profile.
3. Guardar con nombre `DTMAPI_SUBSCRIPTION_KEY` en GitHub Actions secrets.
4. Para HNA (necesidades, acceso separado) solicitar también la API HNA y guardar `DTMHNA_SUBSCRIPTION_KEY` si se aprueba.

**Atención:** todavía no hay scripts DTM vinculados al workflow. Al recibir confirmación de acceso se integrarán sin exponer la clave.

Documentación: https://dtmapi.readthedocs.io/en/latest/

## 3. ReliefWeb — prioridad 1

Documentación y formulario de solicitud de `appname`: https://apidoc.reliefweb.int/

1. Solicitar `appname` con organización, finalidad de investigación y seguimiento humanitario, y datos de contacto institucional.
2. Tras su aprobación, guardarlo bajo `RELIEFWEB_APPNAME` como variable o secreto de GitHub.
3. Para consultar informes NO pedir credenciales de Publish API (solo serían necesarias si OPS quisiera publicar reportes en ReliefWeb).

La integración en scripts está pendiente; la aprobación `appname` es requisito.

## 4. ACLED — licencia de sector público obligatoria para OPS

Documentación: https://acleddata.com/api-documentation/getting-started
Licencia vigente (01/11/2026): https://acleddata.com/eula
Formulario: https://acleddata.com/request-daily-data

Solicitar explícitamente **licencia para organismo multilateral** y autorización para análisis georreferenciado, uso operacional interno y, si procede, publicación de agregados y gráficos. **No asumir** que una cuenta personal concede permiso institucional. ACLED utiliza myACLED y OAuth para scripts.

Tras aprobación, coordinar con ITS el método institucional para custodiar credenciales. No guardar contraseñas de cuentas personales sin permiso ni subir eventos restringidos a un repositorio público. Los términos de ACLED restringen redistribución de datos y acceso automatizado.

## 5. ACNUR — acceso público, permiso de uso continuado por terceros

Documentación: https://refugeedata.unhcr.org/en/documentation/technical-reference/api/

API abierta, sin token. Ya se comprobó la conectividad en cinco países piloto. Para un dashboard operativo con actualización recurrente, contactar a ACNUR porque su documentación dice que el API analítico no está pensado como backend permanente de terceros. Guardar copias locales de series descargadas según licencias y política de privacidad.

## 6. OMS SSA — descarga pública Excel

Portal: https://extranet.who.int/ssa/Index.aspx

Filtrar la tabla de ataques y usar Export to Excel; las exportaciones respetan los filtros. El contenido es sensible: solo se puede publicar lo que aparece públicamente, y las cifras de ataques no son equivalentes a establecimientos únicos.

## Configurar secretos en GitHub (propietario del repo)

Repositorio: https://github.com/ivanromero0724/observatorio-humanitario-ops

- Ir a **Settings → Secrets and variables → Actions**.
- Seleccionar **New repository secret**.
- Introducir el nombre EXACTO (p. ej. `HDX_APP_IDENTIFIER`) y el valor recibido del proveedor.
- Guardar y confirmar únicamente que quedó creado; **NO** pegar el valor en mensajes, documentos, Issues, PRs ni archivos.
- Solicitar integración cuando estén habilitados: HAPI ya está cableado; DTM y ReliefWeb requieren scripts nuevos.

Se debe coordinar con OPS/ITS la propiedad institucional de cuentas, permisos y almacenamiento. Este repositorio es público, por lo que no se deben publicar credenciales ni conjuntos de microdatos restringidos.
