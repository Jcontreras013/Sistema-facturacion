"""Capa de integración para facturación electrónica (DTE) ante el SAR.

El SAR exige que el timbrado electrónico se haga a través de un Proveedor de
Servicios Autorizado (PSA) certificado, con sus propias credenciales y
especificaciones técnicas (firma digital, envío en tiempo real, código QR).

Este módulo define la interfaz que tendría esa integración, pero **no incluye
ningún proveedor real conectado**. Su único trabajo hoy es reportar con
honestidad que no hay nada conectado, para que el estado de cada venta
(`Sale.dte_status`) nunca diga "aceptada" sin que eso haya pasado de verdad.

Cuando el negocio contrate un PSA, se implementa una subclase de
`ElectronicInvoicingProvider` para ese proveedor específico (con su propio
formato de firma y su propio endpoint) y se conecta en `get_provider()`.
"""


class ElectronicInvoicingProvider:
    """Interfaz de un proveedor de facturación electrónica. La implementación base
    no está conectada a nada: existe para que el resto del sistema (POS, detalle de
    venta, configuración) tenga un solo lugar de donde preguntar el estado real."""

    def __init__(self, company):
        self.company = company

    def is_connected(self):
        """True solo cuando existe una implementación real con credenciales válidas."""
        return False

    def send_invoice(self, sale):
        """Firmaría y enviaría la venta al SAR a través del PSA. No implementado."""
        raise NotImplementedError(
            "No hay un proveedor de facturación electrónica certificado conectado. "
            "Configura uno en Admin → Configuración del negocio → Facturación electrónica (DTE)."
        )


def get_provider(company):
    """Punto único para obtener el proveedor de DTE configurado. Hoy siempre
    devuelve la implementación no conectada — reemplazar aquí cuando se integre
    un PSA real."""
    return ElectronicInvoicingProvider(company)
