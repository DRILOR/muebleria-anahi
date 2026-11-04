"""Comando de administración para poblar la base de datos con datos de demostración realistas.

Simula aproximadamente 6 meses de historial comercial continuo para Mueblería Anahí:
- Categorías y catálogo de productos con medidas de fabricación.
- Proveedores locales y materiales con unidades de medida oficiales.
- Compras históricas con actualización de stock de materiales e inventario.
- Consumos de materiales en taller para fabricación.
- Clientes con datos de contacto realistas.
- Ventas históricas (algunas de un producto, otras de múltiples productos).
- Descuento automático de stock de productos terminados.
- Anulaciones de venta con restitución de inventario para trazabilidad de auditoría.
- Idempotente: ejecutarlo múltiples veces no duplica los registros.
- Soporta `--dry-run` para previsualizar sin alterar la base de datos.
"""

from datetime import timedelta
from decimal import Decimal
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from compras.models import Compra, DetalleCompra, Proveedor
from compras.services import registrar_compra
from inventario.models import (
    Categoria,
    Material,
    MedidaProducto,
    MovimientoInventario,
    Producto,
)
from inventario.services import registrar_movimiento
from ventas.models import (
    Cliente,
    DetalleVenta,
    Ingreso,
    MovimientoProducto,
    Venta,
)
from ventas.services import anular_venta, registrar_venta


CATEGORIAS_DATA = [
    {
        "nombre": "Dormitorio",
        "descripcion": "Camas, roperos, cómodas, mesas de noche y respaldos.",
    },
    {
        "nombre": "Comedor y Sala",
        "descripcion": "Mesas de comedor, sillas de madera, mesas de centro y modulares.",
    },
    {
        "nombre": "Oficina y Estudio",
        "descripcion": "Escritorios ejecutivos, estantes, libreros y archivadores.",
    },
    {
        "nombre": "Cocina",
        "descripcion": "Modulares de cocina, alacenas superiores e inferiores y barras.",
    },
    {
        "nombre": "Muebles Auxiliares",
        "descripcion": "Repisas flotantes, percheros, zapateras y baúles organizadores.",
    },
]


PROVEEDORES_DATA = [
    {
        "nombre": "Maderas del Valle S.R.L.",
        "nit": "1029384019",
        "telefono": "71029384",
        "email": "ventas@maderasdelvalle.com.bo",
        "direccion": "Km 8 Doble Vía a La Guardia, Santa Cruz",
    },
    {
        "nombre": "Distribuidora El Carpintero",
        "nit": "2039485012",
        "telefono": "72093847",
        "email": "pedidos@elcarpintero.bo",
        "direccion": "Av. Juan Pablo II Nro 1420, El Alto, La Paz",
    },
    {
        "nombre": "Insumos Forestales del Sur",
        "nit": "3049586023",
        "telefono": "73094856",
        "email": "contacto@forestalesdelsur.bo",
        "direccion": "Av. Panamericana Nro 850, Tarija",
    },
    {
        "nombre": "Ferretería Industrial Andina",
        "nit": "4059687034",
        "telefono": "74095867",
        "email": "informes@andinaferretera.bo",
        "direccion": "Av. Blanco Galindo Km 3, Cochabamba",
    },
    {
        "nombre": "Melaminas & Diseños Bolivia",
        "nit": "5069788045",
        "telefono": "75096878",
        "email": "ventas@melaminasbolivia.bo",
        "direccion": "Parque Industrial Mz 12, Santa Cruz",
    },
    {
        "nombre": "Accesorios y Herrajes del Oriente",
        "nit": "6079889056",
        "telefono": "76097889",
        "email": "herrajes@orienteherrajes.bo",
        "direccion": "Av. Circunvalación Nro 340, Montero",
    },
    {
        "nombre": "Importadora Bosques del Chaco",
        "nit": "7089990067",
        "telefono": "77098890",
        "email": "bosqueschaco@gmail.com",
        "direccion": "Calle Comercio Nro 520, Yacuiba",
    },
    {
        "nombre": "Herrajes & Chapas San Pedro",
        "nit": "8090101078",
        "telefono": "78099901",
        "email": "ventas@herrajessanpedro.bo",
        "direccion": "Calle Colombia Nro 215, La Paz",
    },
    {
        "nombre": "Química Maderera del Altiplano",
        "nit": "9101212089",
        "telefono": "79100012",
        "email": "contacto@quimicamaderera.bo",
        "direccion": "Zona Villa Bolívar D Nro 45, El Alto",
    },
    {
        "nombre": "Telas & Cueros Industriales",
        "nit": "1212323090",
        "telefono": "70111223",
        "email": "ventas@telasindustriales.bo",
        "direccion": "Calle Esteban Arce Nro 780, Cochabamba",
    },
    {
        "nombre": "Maderera y Barraca Chapare",
        "nit": "2323434101",
        "telefono": "71222334",
        "email": "barracachapare@gmail.com",
        "direccion": "Ruta 4 Km 15, Chimoré, Cochabamba",
    },
    {
        "nombre": "Tornillería Central Boliviana",
        "nit": "3434545212",
        "telefono": "72333445",
        "email": "pedidos@tornilleriacentral.bo",
        "direccion": "Av. 6 de Agosto Nro 1120, Cochabamba",
    },
]


MATERIALES_DATA = [
    # Maderas (TABLON, METRO)
    {"codigo": "MAT-MAD-001", "nombre": "Madera de Roble Nacional", "unidad_medida": Material.TABLON, "costo_referencia": "85.00", "stock_minimo": "15.00"},
    {"codigo": "MAT-MAD-002", "nombre": "Madera de Cedro Amargo", "unidad_medida": Material.TABLON, "costo_referencia": "110.00", "stock_minimo": "10.00"},
    {"codigo": "MAT-MAD-003", "nombre": "Madera de Pino Radiata Tratado", "unidad_medida": Material.TABLON, "costo_referencia": "45.00", "stock_minimo": "20.00"},
    {"codigo": "MAT-MAD-004", "nombre": "Madera de Mara / Caoba", "unidad_medida": Material.TABLON, "costo_referencia": "165.00", "stock_minimo": "5.00"},
    {"codigo": "MAT-MAD-005", "nombre": "Listones de Tajibo 2x2 pulgadas", "unidad_medida": Material.METRO, "costo_referencia": "18.00", "stock_minimo": "30.00"},
    {"codigo": "MAT-MAD-006", "nombre": "Tirantes de Almendrillo 2x4", "unidad_medida": Material.METRO, "costo_referencia": "26.00", "stock_minimo": "20.00"},
    # Tableros (M2)
    {"codigo": "MAT-TAB-001", "nombre": "Tablero Melamínico Blanco 18mm", "unidad_medida": Material.METRO_CUADRADO, "costo_referencia": "65.00", "stock_minimo": "15.00"},
    {"codigo": "MAT-TAB-002", "nombre": "Tablero Melamínico Roble Santana 18mm", "unidad_medida": Material.METRO_CUADRADO, "costo_referencia": "78.00", "stock_minimo": "12.00"},
    {"codigo": "MAT-TAB-003", "nombre": "Tablero Melamínico Nogal Terracota 18mm", "unidad_medida": Material.METRO_CUADRADO, "costo_referencia": "82.00", "stock_minimo": "10.00"},
    {"codigo": "MAT-TAB-004", "nombre": "Tablero MDF Crudo 15mm", "unidad_medida": Material.METRO_CUADRADO, "costo_referencia": "48.00", "stock_minimo": "15.00"},
    {"codigo": "MAT-TAB-005", "nombre": "Tablero MDF Crudo 9mm", "unidad_medida": Material.METRO_CUADRADO, "costo_referencia": "35.00", "stock_minimo": "10.00"},
    {"codigo": "MAT-TAB-006", "nombre": "Triplay Venesta 4mm", "unidad_medida": Material.METRO_CUADRADO, "costo_referencia": "28.00", "stock_minimo": "20.00"},
    # Herrajes (UNIDAD, METRO, KG)
    {"codigo": "MAT-HER-001", "nombre": "Bisagras Cazoleta Cierre Lento 35mm", "unidad_medida": Material.UNIDAD, "costo_referencia": "8.50", "stock_minimo": "50.00"},
    {"codigo": "MAT-HER-002", "nombre": "Bisagras Cazoleta Recta estándar", "unidad_medida": Material.UNIDAD, "costo_referencia": "5.00", "stock_minimo": "60.00"},
    {"codigo": "MAT-HER-003", "nombre": "Correderas Telescópicas Pesadas 45cm", "unidad_medida": Material.UNIDAD, "costo_referencia": "24.00", "stock_minimo": "25.00"},
    {"codigo": "MAT-HER-004", "nombre": "Correderas Telescópicas Estándar 40cm", "unidad_medida": Material.UNIDAD, "costo_referencia": "18.00", "stock_minimo": "30.00"},
    {"codigo": "MAT-HER-005", "nombre": "Tiradores Metálicos Negro Mate 160mm", "unidad_medida": Material.UNIDAD, "costo_referencia": "12.00", "stock_minimo": "40.00"},
    {"codigo": "MAT-HER-006", "nombre": "Tiradores Perfil de Aluminio", "unidad_medida": Material.METRO, "costo_referencia": "25.00", "stock_minimo": "15.00"},
    {"codigo": "MAT-HER-007", "nombre": "Cerraduras para Cajón de Escritorio", "unidad_medida": Material.UNIDAD, "costo_referencia": "19.00", "stock_minimo": "10.00"},
    {"codigo": "MAT-HER-008", "nombre": "Tornillos Autorroscantes 3.5x16mm", "unidad_medida": Material.UNIDAD, "costo_referencia": "0.10", "stock_minimo": "500.00"},
    {"codigo": "MAT-HER-009", "nombre": "Tornillos Soberbios para Madera 4x50mm", "unidad_medida": Material.UNIDAD, "costo_referencia": "0.25", "stock_minimo": "400.00"},
    {"codigo": "MAT-HER-010", "nombre": "Clavos con Cabeza 2 pulgadas", "unidad_medida": Material.KILOGRAMO, "costo_referencia": "14.00", "stock_minimo": "10.00"},
    # Acabados y Químicos (LITRO, UNIDAD, METRO)
    {"codigo": "MAT-ACA-001", "nombre": "Cola Fría D3 para Madera", "unidad_medida": Material.LITRO, "costo_referencia": "32.00", "stock_minimo": "15.00"},
    {"codigo": "MAT-ACA-002", "nombre": "Barniz Poliuretano Brillante", "unidad_medida": Material.LITRO, "costo_referencia": "55.00", "stock_minimo": "10.00"},
    {"codigo": "MAT-ACA-003", "nombre": "Barniz Poliuretano Mate", "unidad_medida": Material.LITRO, "costo_referencia": "58.00", "stock_minimo": "10.00"},
    {"codigo": "MAT-ACA-004", "nombre": "Sellador Nitrocelulósico Concentrado", "unidad_medida": Material.LITRO, "costo_referencia": "42.00", "stock_minimo": "12.00"},
    {"codigo": "MAT-ACA-005", "nombre": "Tinner Corriente Extra Fino", "unidad_medida": Material.LITRO, "costo_referencia": "18.00", "stock_minimo": "25.00"},
    {"codigo": "MAT-ACA-006", "nombre": "Lija al Agua grano 220", "unidad_medida": Material.UNIDAD, "costo_referencia": "4.50", "stock_minimo": "50.00"},
    {"codigo": "MAT-ACA-007", "nombre": "Canto PVC Grueso 2mm Roble", "unidad_medida": Material.METRO, "costo_referencia": "3.50", "stock_minimo": "80.00"},
    # Tapicería (M2, METRO)
    {"codigo": "MAT-TAP-001", "nombre": "Espuma de Alta Densidad D-28", "unidad_medida": Material.METRO_CUADRADO, "costo_referencia": "65.00", "stock_minimo": "8.00"},
    {"codigo": "MAT-TAP-002", "nombre": "Tela Chenille Antimanchas Gris", "unidad_medida": Material.METRO, "costo_referencia": "48.00", "stock_minimo": "15.00"},
]


PRODUCTOS_DATA = [
    # Dormitorio
    {"codigo": "PRD-DOR-001", "nombre": "Cama matrimonial 2 plazas", "cat": "Dormitorio", "precio": "2800.00", "min": 2, "stock_obj": 5, "alto": 110, "ancho": 160, "prof": 205, "desc": "Estructura maciza de roble con largueros reforzados."},
    {"codigo": "PRD-DOR-002", "nombre": "Cama King Size con cabecera acolchada", "cat": "Dormitorio", "precio": "4200.00", "min": 2, "stock_obj": 3, "alto": 125, "ancho": 200, "prof": 215, "desc": "Estructura en cedro y tapizado con tela chenille antimanchas."},
    {"codigo": "PRD-DOR-003", "nombre": "Cama plaza y media juvenil", "cat": "Dormitorio", "precio": "1750.00", "min": 3, "stock_obj": 8, "alto": 95, "ancho": 115, "prof": 200, "desc": "Fabricada en pino seleccionado con acabado sellador mate."},
    {"codigo": "PRD-DOR-004", "nombre": "Cama cucheta / litera desmontable", "cat": "Dormitorio", "precio": "2900.00", "min": 2, "stock_obj": 4, "alto": 165, "ancho": 115, "prof": 205, "desc": "Madera maciza desmontable en dos camas independientes."},
    {"codigo": "PRD-DOR-005", "nombre": "Ropero 3 puertas con cajonería", "cat": "Dormitorio", "precio": "3100.00", "min": 2, "stock_obj": 3, "alto": 200, "ancho": 150, "prof": 58, "desc": "Interior con colgadores y 4 cajones con correderas telescópicas."},
    {"codigo": "PRD-DOR-006", "nombre": "Ropero 4 puertas con espejo central", "cat": "Dormitorio", "precio": "4400.00", "min": 2, "stock_obj": 0, "alto": 210, "ancho": 200, "prof": 60, "desc": "Ropero amplio en cedro con espejo biselado. (Agotado por alta demanda)."},
    {"codigo": "PRD-DOR-007", "nombre": "Ropero empotrado modular de melamina", "cat": "Dormitorio", "precio": "3800.00", "min": 2, "stock_obj": 4, "alto": 220, "ancho": 180, "prof": 60, "desc": "Melamina roble santana de 18mm con perfiles de aluminio."},
    {"codigo": "PRD-DOR-008", "nombre": "Cómoda de 6 cajones", "cat": "Dormitorio", "precio": "1950.00", "min": 3, "stock_obj": 2, "alto": 110, "ancho": 120, "prof": 48, "desc": "Cómoda amplia de cedro (Stock bajo)."},
    {"codigo": "PRD-DOR-009", "nombre": "Mesa de noche de 2 cajones", "cat": "Dormitorio", "precio": "520.00", "min": 4, "stock_obj": 14, "alto": 60, "ancho": 48, "prof": 40, "desc": "Velador en madera de roble barnizada (Stock abundante)."},
    {"codigo": "PRD-DOR-010", "nombre": "Mesa de noche minimalista melamina", "cat": "Dormitorio", "precio": "380.00", "min": 4, "stock_obj": 11, "alto": 55, "ancho": 45, "prof": 38, "desc": "Velador moderno flotante blanco."},
    {"codigo": "PRD-DOR-011", "nombre": "Juego de dormitorio imperial", "cat": "Dormitorio", "precio": "5800.00", "min": 1, "stock_obj": 0, "alto": 125, "ancho": 200, "prof": 215, "desc": "Conjunto exclusivo de cama king, 2 veladores y cómoda (Agotado)."},
    # Comedor y Sala
    {"codigo": "PRD-SAL-001", "nombre": "Mesa de comedor de 6 sillas", "cat": "Comedor y Sala", "precio": "3950.00", "min": 2, "stock_obj": 4, "alto": 78, "ancho": 180, "prof": 90, "desc": "Tablero macizo de roble con patas gruesas torneadas."},
    {"codigo": "PRD-SAL-002", "nombre": "Mesa de comedor de 8 sillas", "cat": "Comedor y Sala", "precio": "5600.00", "min": 2, "stock_obj": 1, "alto": 78, "ancho": 240, "prof": 100, "desc": "Comedor familiar en cedro (Stock bajo, 1 unidad)."},
    {"codigo": "PRD-SAL-003", "nombre": "Mesa de comedor redonda 4 puestos", "cat": "Comedor y Sala", "precio": "2400.00", "min": 2, "stock_obj": 3, "alto": 76, "ancho": 110, "prof": 110, "desc": "Base central cilíndrica de diseño contemporáneo."},
    {"codigo": "PRD-SAL-004", "nombre": "Silla de madera clásica", "cat": "Comedor y Sala", "precio": "280.00", "min": 6, "stock_obj": 22, "alto": 95, "ancho": 45, "prof": 46, "desc": "Silla resistente con respaldo ergonómico de madera (Stock abundante)."},
    {"codigo": "PRD-SAL-005", "nombre": "Silla de comedor tapizada chenille", "cat": "Comedor y Sala", "precio": "390.00", "min": 6, "stock_obj": 18, "alto": 96, "ancho": 48, "prof": 50, "desc": "Asiento acolchado con espuma de alta densidad (Stock abundante)."},
    {"codigo": "PRD-SAL-006", "nombre": "Mesa de centro rústica", "cat": "Comedor y Sala", "precio": "750.00", "min": 3, "stock_obj": 7, "alto": 45, "ancho": 100, "prof": 60, "desc": "Mesa de centro en madera maciza con repisa para revistas."},
    {"codigo": "PRD-SAL-007", "nombre": "Mesa de centro moderna de vidrio y roble", "cat": "Comedor y Sala", "precio": "950.00", "min": 2, "stock_obj": 5, "alto": 42, "ancho": 110, "prof": 65, "desc": "Diseño nórdico con vidrio templado de 8mm."},
    {"codigo": "PRD-SAL-008", "nombre": "Mueble para televisión hasta 65 pulgadas", "cat": "Comedor y Sala", "precio": "1850.00", "min": 2, "stock_obj": 6, "alto": 60, "ancho": 180, "prof": 45, "desc": "Modular bajo con pasa cables y puertas corredizas."},
    {"codigo": "PRD-SAL-009", "nombre": "Panel flotante para televisor con LED", "cat": "Comedor y Sala", "precio": "1250.00", "min": 2, "stock_obj": 5, "alto": 140, "ancho": 160, "prof": 22, "desc": "Panel en melamina nogal con iluminación cálida posterior."},
    {"codigo": "PRD-SAL-010", "nombre": "Aparador buffet de 4 puertas", "cat": "Comedor y Sala", "precio": "2700.00", "min": 2, "stock_obj": 3, "alto": 90, "ancho": 160, "prof": 45, "desc": "Mueble aparador con repisas interiores ajustables."},
    {"codigo": "PRD-SAL-011", "nombre": "Vitrina esquinera con cristalería", "cat": "Comedor y Sala", "precio": "2200.00", "min": 1, "stock_obj": 0, "alto": 185, "ancho": 65, "prof": 65, "desc": "Vitrina clásica de esquina con 3 repisas de vidrio (Agotado)."},
    # Oficina y Estudio
    {"codigo": "PRD-OFI-001", "nombre": "Escritorio ejecutivo en L con cajonería", "cat": "Oficina y Estudio", "precio": "3400.00", "min": 2, "stock_obj": 4, "alto": 76, "ancho": 180, "prof": 150, "desc": "Superficie de roble con cajón archivador y llave central."},
    {"codigo": "PRD-OFI-002", "nombre": "Escritorio estudiantil compacto", "cat": "Oficina y Estudio", "precio": "890.00", "min": 3, "stock_obj": 8, "alto": 75, "ancho": 100, "prof": 55, "desc": "Escritorio juvenil con repisa superior para libros."},
    {"codigo": "PRD-OFI-003", "nombre": "Escritorio home office moderno", "cat": "Oficina y Estudio", "precio": "1350.00", "min": 3, "stock_obj": 6, "alto": 76, "ancho": 130, "prof": 60, "desc": "Estructura metálica negra y tablero melamínico roble."},
    {"codigo": "PRD-OFI-004", "nombre": "Librero alto de 5 niveles", "cat": "Oficina y Estudio", "precio": "1650.00", "min": 2, "stock_obj": 5, "alto": 190, "ancho": 90, "prof": 32, "desc": "Librero resistente con repisas de 3cm de grosor."},
    {"codigo": "PRD-OFI-005", "nombre": "Estantería modular de madera y metal", "cat": "Oficina y Estudio", "precio": "1450.00", "min": 2, "stock_obj": 7, "alto": 180, "ancho": 100, "prof": 35, "desc": "Estantería estilo industrial para libros y decoración."},
    {"codigo": "PRD-OFI-006", "nombre": "Archivador de madera de 3 cajones", "cat": "Oficina y Estudio", "precio": "980.00", "min": 2, "stock_obj": 2, "alto": 105, "ancho": 48, "prof": 55, "desc": "Gavetero para carpetas colgantes oficio (Stock bajo)."},
    # Cocina
    {"codigo": "PRD-COC-001", "nombre": "Modular de cocina bajo mesada 1.50m", "cat": "Cocina", "precio": "2650.00", "min": 2, "stock_obj": 3, "alto": 85, "ancho": 150, "prof": 60, "desc": "Cuerpo melamínico resistente al agua con tiradores negros."},
    {"codigo": "PRD-COC-002", "nombre": "Alacena de cocina aérea 1.50m", "cat": "Cocina", "precio": "1850.00", "min": 2, "stock_obj": 4, "alto": 70, "ancho": 150, "prof": 35, "desc": "Módulo superior con pistones a gas y puertas vidriadas."},
    {"codigo": "PRD-COC-003", "nombre": "Mueble despensero vertical 2 puertas", "cat": "Cocina", "precio": "1750.00", "min": 2, "stock_obj": 1, "alto": 195, "ancho": 60, "prof": 45, "desc": "Despensero de 5 compartimientos (Stock bajo, 1 unidad)."},
    {"codigo": "PRD-COC-004", "nombre": "Barra desayunadora con 2 banquetas", "cat": "Cocina", "precio": "1980.00", "min": 2, "stock_obj": 3, "alto": 100, "ancho": 140, "prof": 50, "desc": "Barra alta de madera con dos taburetes a juego."},
    # Muebles Auxiliares
    {"codigo": "PRD-AUX-001", "nombre": "Repisa flotante de madera 80cm", "cat": "Muebles Auxiliares", "precio": "160.00", "min": 5, "stock_obj": 25, "alto": 4, "ancho": 80, "prof": 22, "desc": "Soporte oculto con capacidad de carga de 20 kg (Stock abundante)."},
    {"codigo": "PRD-AUX-002", "nombre": "Zapatera organizadora para 18 pares", "cat": "Muebles Auxiliares", "precio": "790.00", "min": 3, "stock_obj": 6, "alto": 115, "ancho": 75, "prof": 30, "desc": "Mueble zapatero con 3 trampones basculantes."},
    {"codigo": "PRD-AUX-003", "nombre": "Perchero de pie de madera torneada", "cat": "Muebles Auxiliares", "precio": "320.00", "min": 3, "stock_obj": 12, "alto": 175, "ancho": 45, "prof": 45, "desc": "Perchero clásico con 8 ganchos para abrigos y sombreros."},
    {"codigo": "PRD-AUX-004", "nombre": "Baúl organizador para pie de cama", "cat": "Muebles Auxiliares", "precio": "880.00", "min": 2, "stock_obj": 5, "alto": 50, "ancho": 110, "prof": 45, "desc": "Baúl tapizado con bisagras de freno neumático."},
]


CLIENTES_DATA = [
    ("Carlos Mamani Colque", "4839201", "71011223", "carlos.mamani.bo@gmail.com", "Barrio Equipetrol Calle 7 Nro 120, Santa Cruz"),
    ("Valeria Gutiérrez Paz", "5928192", "72022334", "valeria.gtz.bo@hotmail.com", "Av. Arce Nro 2340 Edif. Mirador, La Paz"),
    ("Jorge Fernández Rojas", "3847291", "73033445", "jorge.fernandez77@gmail.com", "Zona Cala Cala Calle Rosales Nro 45, Cochabamba"),
    ("Patricia Quispe Flores", "6718293", "74044556", "patricia.quispe.fl@yahoo.com", "Calle Sucre Nro 890, Tarija"),
    ("Fernando Arteaga Suárez", "4918273", "75055667", "fernando.arteaga@gmail.com", "Barrio Hamacas Calle 4 Nro 210, Santa Cruz"),
    ("Mariana Vargas Peñaranda", "5827182", "76066778", "mariana.vargas.bo@gmail.com", "Zona Sopocachi Calle Ecuador Nro 670, La Paz"),
    ("Roberto Torrico Morales", "3718294", "77077889", "roberto.torrico.cbba@hotmail.com", "Av. América Oeste Nro 1145, Cochabamba"),
    ("Claudia Mendoza Alarcón", "6829103", "78088990", "claudia.mendoza.tja@gmail.com", "Barrio El Molino Calle Colón Nro 340, Tarija"),
    ("Alejandro Justiniano Vaca", "4029183", "79099001", "ale.justiniano.scz@gmail.com", "Av. Banzer Km 5 Nro 82, Santa Cruz"),
    ("Gabriela Choquehuanca Ruiz", "5192837", "70122334", "gabriela.choque.lp@yahoo.com", "Zona Miraflores Calle Díaz Romero Nro 145, La Paz"),
    ("Marcelo Claure Zambrana", "3291823", "71233445", "marcelo.claure.z@gmail.com", "Zona Sarco Calle Las Violetas Nro 78, Cochabamba"),
    ("Paola Barrientos Durán", "6382910", "72344556", "paola.barrientos.scz@hotmail.com", "Barrio Las Palmas Calle 3 Nro 56, Santa Cruz"),
    ("Guillermo Roca Monasterio", "4472819", "73455667", "guillermo.roca.scz@gmail.com", "Villa Primero de Mayo Calle 10 Nro 34, Santa Cruz"),
    ("Daniela Mercado Siles", "5581920", "74566778", "daniela.mercado.lp@gmail.com", "Zona Calacoto Calle 15 Nro 8200, La Paz"),
    ("Hugo Villarroel Crespo", "3692817", "75677889", "hugo.villarroel.cbba@yahoo.com", "Av. Beijing Nro 450, Cochabamba"),
    ("Lucía Romero Baldiviezo", "6701928", "76788990", "lucia.romero.tja@gmail.com", "Barrio San Roque Calle Campero Nro 210, Tarija"),
    ("Rodrigo Melgar Ribera", "4810293", "77899001", "rodrigo.melgar.bo@hotmail.com", "Barrio Urbarí Calle Los Sauces Nro 112, Santa Cruz"),
    ("Elena Camacho Zurita", "5921038", "78900112", "elena.camacho.cbba@gmail.com", "Zona Queru Queru Calle Paccieri Nro 67, Cochabamba"),
    ("Sergio Mercado Benítez", "3032149", "79011223", "sergio.mercado.bo@gmail.com", "Zona Achumani Calle 22 Nro 140, La Paz"),
    ("Camila Soliz Hurtado", "6143250", "70122445", "camila.soliz.scz@yahoo.com", "Barrio Sirari Calle Las Palmeras Nro 88, Santa Cruz"),
    ("Diego Aramayo Quiroga", "4254361", "71233556", "diego.aramayo.tja@gmail.com", "Barrio Fátima Calle Belgrano Nro 420, Tarija"),
    ("Natalia Prado Zeballos", "5365472", "72344667", "natalia.prado.lp@hotmail.com", "Zona Obrajes Calle 10 Nro 310, La Paz"),
    ("Javier Cossio Bustamante", "3476583", "73455778", "javier.cossio.cbba@gmail.com", "Zona Recoleta Calle Beni Nro 89, Cochabamba"),
    ("Andrea Aguilera Cuéllar", "6587694", "74566889", "andrea.aguilera.scz@gmail.com", "Av. San Martín Nro 1250, Santa Cruz"),
    ("Mauricio Zabaleta Pinto", "4698705", "75677990", "mauricio.zabaleta.bo@yahoo.com", "Zona Cota Cota Calle 29 Nro 75, La Paz"),
    ("Lorena Céspedes Terán", "5709816", "76788001", "lorena.cespedes.cbba@gmail.com", "Av. América Este Nro 670, Cochabamba"),
    ("Gonzalo Saucedo Antelo", "3810927", "77899112", "gonzalo.saucedo.scz@hotmail.com", "Barrio Urbari Calle Toborochi Nro 45, Santa Cruz"),
    ("Sofía Miranda Osinaga", "6921038", "78900223", "sofia.miranda.tja@gmail.com", "Calle La Madrid Nro 560, Tarija"),
    ("Esteban Claros Hinojosa", "4032149", "79011334", "esteban.claros.cbba@gmail.com", "Zona Tupuraya Calle Rosales Nro 114, Cochabamba"),
    ("Verónica Tórrez Medina", "5143250", "70122556", "veronica.torrez.lp@gmail.com", "Zona San Jorge Av. Arce Nro 2780, La Paz"),
    ("Raúl Escalante Rivero", "3254361", "71233667", "raul.escalante.scz@yahoo.com", "Barrio Conavi Calle 5 Nro 32, Montero"),
    ("Silvia Calderón Montero", "6365472", "72344778", "silvia.calderon.bo@gmail.com", "Zona Bajo Següencoma Calle 2 Nro 89, La Paz"),
    ("Christian Arnez Ferrufino", "4476583", "73455889", "christian.arnez.cbba@hotmail.com", "Av. D'Orbigny Nro 890, Cochabamba"),
    ("Renata Chávez Salvatierra", "5587694", "74566990", "renata.chavez.scz@gmail.com", "Barrio Los Choferes Calle 2 Nro 110, Santa Cruz"),
    ("Óscar Leytón Coronado", "3698705", "75677001", "oscar.leyton.tja@gmail.com", "Barrio Las Panosas Calle Méndez Nro 230, Tarija"),
    ("Adriana Loza Cardozo", "6709816", "76788112", "adriana.loza.lp@yahoo.com", "Zona Villa Fátima Calle 3 Nro 45, La Paz"),
    ("Víctor Hugo Paz Estenssoro", "4810927", "77899223", "victorhugo.paz.tja@gmail.com", "Barrio San Bernardo Calle Sucre Nro 890, Tarija"),
    ("Beatriz Salinas Sandoval", "7932104", "78900334", "beatriz.salinas.scz@hotmail.com", "Av. San Aurelio 4to Anillo Nro 450, Santa Cruz"),
    ("Álvaro Bellido Carvallo", "3032150", "79011445", "alvaro.bellido.cbba@gmail.com", "Zona Temporal Calle Manzano Nro 12, Cochabamba"),
    ("Cecilia Monje Alurralde", "6143261", "70122667", "cecilia.monje.lp@gmail.com", "Zona Irpavi Calle 8 Nro 340, La Paz"),
]


class Command(BaseCommand):
    help = "Carga datos de prueba realistas para Mueblería Anahí (6 meses de historial comercial)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula la generación de datos sin guardar cambios en la base de datos.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Muestra detalles extendidos de cada operación ejecutada.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        verbose = options.get("verbose", False)

        self.stdout.write(self.style.MIGRATE_HEADING("=== MUEBLERÍA ANAHÍ — CARGA DE DATOS DE DEMOSTRACIÓN ==="))
        if dry_run:
            self.stdout.write(self.style.WARNING("MODO SIMULACIÓN (--dry-run ACTIVADO): No se guardará ningún cambio."))

        # 1. Obtener usuario de referencia para auditoría
        User = get_user_model()
        usuario = User.objects.filter(is_superuser=True).first() or User.objects.first()

        try:
            with transaction.atomic():
                resumen = self._ejecutar_carga(usuario, verbose=verbose)

                if dry_run:
                    transaction.set_rollback(True)
                    self.stdout.write(self.style.WARNING("\nSimulación completada con éxito. Transacción revertida (--dry-run)."))
                else:
                    self.stdout.write(self.style.SUCCESS("\n¡Carga de datos de demostración completada y guardada con éxito!"))

                self._imprimir_resumen(resumen, dry_run=dry_run)

        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"\nERROR durante la carga de demostración: {exc}"))
            raise exc

    def _ejecutar_carga(self, usuario, verbose=False):
        ahora = timezone.now()

        # A. Categorías
        categorias_creadas = 0
        cat_map = {}
        for cdata in CATEGORIAS_DATA:
            cat, created = Categoria.objects.get_or_create(
                nombre=cdata["nombre"],
                defaults={"descripcion": cdata["descripcion"], "activo": True},
            )
            cat_map[cat.nombre] = cat
            if created:
                categorias_creadas += 1

        # B. Proveedores (12)
        proveedores_creados = 0
        prov_list = []
        for pdata in PROVEEDORES_DATA:
            prov, created = Proveedor.objects.get_or_create(
                nombre=pdata["nombre"],
                defaults={
                    "nit": pdata["nit"],
                    "telefono": pdata["telefono"],
                    "email": pdata["email"],
                    "direccion": pdata["direccion"],
                    "activo": True,
                },
            )
            prov_list.append(prov)
            if created:
                proveedores_creados += 1

        # C. Materiales (30)
        materiales_creados = 0
        mat_map = {}
        for mdata in MATERIALES_DATA:
            mat, created = Material.objects.get_or_create(
                codigo=mdata["codigo"],
                defaults={
                    "nombre": mdata["nombre"],
                    "unidad_medida": mdata["unidad_medida"],
                    "costo_referencia": Decimal(mdata["costo_referencia"]),
                    "stock_minimo": Decimal(mdata["stock_minimo"]),
                    "stock": Decimal("0.00"),
                    "activo": True,
                },
            )
            mat_map[mat.codigo] = mat
            if created:
                materiales_creados += 1

        # D. Clientes (40)
        clientes_creados = 0
        cli_list = []
        for nombre, nit, tel, email, dir_cli in CLIENTES_DATA:
            cli, created = Cliente.objects.get_or_create(
                nit=nit,
                defaults={
                    "nombre": nombre,
                    "telefono": tel,
                    "email": email,
                    "direccion": dir_cli,
                    "activo": True,
                },
            )
            cli_list.append(cli)
            if created:
                clientes_creados += 1

        # Pre-planificar las 100 ventas para calcular stock inicial exacto de productos
        # y garantizar que nunca falte stock durante el transcurso histórico
        plan_ventas = self._generar_plan_ventas(len(PRODUCTOS_DATA), len(cli_list))
        indices_anuladas = {12, 28, 45, 62, 78, 88}

        demandas_producto = {i: 0 for i in range(len(PRODUCTOS_DATA))}
        anuladas_producto = {i: 0 for i in range(len(PRODUCTOS_DATA))}

        for v_idx, venta_item in enumerate(plan_ventas):
            for prod_idx, cant in venta_item["lineas"]:
                demandas_producto[prod_idx] += cant
                if v_idx in indices_anuladas:
                    anuladas_producto[prod_idx] += cant

        # E. Productos (36)
        productos_creados = 0
        prod_list = []
        for idx, pdata in enumerate(PRODUCTOS_DATA):
            stock_inicial = pdata["stock_obj"] + demandas_producto[idx] - anuladas_producto[idx]
            categoria = cat_map[pdata["cat"]]

            prod, created = Producto.objects.get_or_create(
                codigo=pdata["codigo"],
                defaults={
                    "nombre": pdata["nombre"],
                    "categoria": categoria,
                    "precio": Decimal(pdata["precio"]),
                    "stock": stock_inicial,
                    "stock_minimo": pdata["min"],
                    "descripcion": pdata["desc"],
                    "activo": True,
                },
            )
            if not created and prod.stock == 0 and stock_inicial > 0:
                # Si el producto existía sin stock para demo, actualizamos al stock inicial planificado
                prod.stock = stock_inicial
                prod.save(update_fields=["stock"])

            prod_list.append(prod)
            if created:
                productos_creados += 1

            # Medidas del producto
            MedidaProducto.objects.get_or_create(
                producto=prod,
                defaults={
                    "alto_cm": Decimal(pdata["alto"]),
                    "ancho_cm": Decimal(pdata["ancho"]),
                    "profundidad_cm": Decimal(pdata["prof"]),
                    "observaciones": f"Medidas estándar de fabricación en carpintería: {pdata['nombre']}.",
                },
            )

        # F. Compras Históricas (45 compras distribuidas en 6 meses)
        compras_creadas = 0
        mat_keys = list(mat_map.keys())

        for c_idx in range(45):
            doc_num = f"DEMO-CMP-{c_idx + 1:03d}"
            if Compra.objects.filter(numero_documento=doc_num).exists():
                continue

            # Días atrás en el tiempo: de 175 a 4 días atrás
            dias_atras = int(175 - (c_idx * 171 / 44))
            fecha_op = ahora - timedelta(days=dias_atras, hours=(c_idx % 8) + 8, minutes=(c_idx * 7) % 60)

            # Selección de proveedor y materiales afines
            prov = prov_list[c_idx % len(prov_list)]
            num_lineas = (c_idx % 3) + 1  # 1 a 3 materiales por compra
            detalles = []

            for offset in range(num_lineas):
                mat_key = mat_keys[(c_idx * 2 + offset) % len(mat_keys)]
                material = mat_map[mat_key]

                # Cantidades coherentes según tipo de material
                if material.unidad_medida in (Material.TABLON, Material.METRO_CUADRADO):
                    cant = Decimal(random.choice([15, 20, 25, 30, 40]))
                elif material.unidad_medida in (Material.METRO, Material.LITRO):
                    cant = Decimal(random.choice([20, 30, 50, 60]))
                elif material.unidad_medida == Material.KILOGRAMO:
                    cant = Decimal(random.choice([15, 25, 40]))
                else:  # UNIDAD
                    cant = Decimal(random.choice([100, 150, 200, 300]))

                costo = (material.costo_referencia * Decimal(random.choice(["0.96", "1.00", "1.04"]))).quantize(Decimal("0.01"))
                detalles.append({
                    "material": material,
                    "cantidad": cant,
                    "costo_unitario": costo,
                })

            compra = registrar_compra(
                proveedor=prov,
                detalles=detalles,
                usuario=usuario,
                numero_documento=doc_num,
                observaciones=f"[DEMO] Adquisición periódica de insumos y materiales #{c_idx + 1:03d}",
            )

            # Ajuste de fechas históricas
            Compra.objects.filter(pk=compra.pk).update(fecha=fecha_op)
            MovimientoInventario.objects.filter(referencia=f"Compra #{compra.pk}").update(fecha=fecha_op)
            compras_creadas += 1

        # G. Consumo en Taller para Fabricación (25 movimientos de salida)
        # Esto equilibra los materiales para que algunos tengan stock normal, otros bajo y algunos agotados
        consumos_creados = 0
        for fab_idx in range(25):
            ref_fab = f"DEMO-FAB-{fab_idx + 1:03d}"
            if MovimientoInventario.objects.filter(referencia=ref_fab).exists():
                continue

            mat_key = mat_keys[(fab_idx * 3) % len(mat_keys)]
            material = mat_map[mat_key]
            material.refresh_from_db()

            dias_atras = int(168 - (fab_idx * 160 / 24))
            fecha_fab = ahora - timedelta(days=dias_atras, hours=10 + (fab_idx % 6), minutes=15)

            # Cantidad que no exceda el stock actual
            if material.stock > Decimal("5.00"):
                cant_consumo = (material.stock * Decimal("0.55")).quantize(Decimal("0.01"))
                if cant_consumo > 0:
                    mov = registrar_movimiento(
                        material_id=material.pk,
                        tipo=MovimientoInventario.SALIDA,
                        cantidad=cant_consumo,
                        motivo=f"[DEMO] Consumo de materiales en taller para fabricación lote #{fab_idx + 1:02d}",
                        usuario=usuario,
                        referencia=ref_fab,
                    )
                    MovimientoInventario.objects.filter(pk=mov.pk).update(fecha=fecha_fab)
                    consumos_creados += 1

        # H. Ventas Históricas (100 ventas distribuidas en 6 meses)
        ventas_creadas = 0
        ventas_anuladas = 0
        metodos_pago = [
            Ingreso.EFECTIVO,
            Ingreso.TRANSFERENCIA,
            Ingreso.EFECTIVO,
            Ingreso.QR,
            Ingreso.TRANSFERENCIA,
            Ingreso.EFECTIVO,
            Ingreso.TARJETA,
            Ingreso.QR,
        ]

        for v_idx, v_plan in enumerate(plan_ventas):
            obs_identificador = f"[DEMO] Venta comercial #{v_idx + 1:03d}"
            if Venta.objects.filter(observaciones__startswith=obs_identificador).exists():
                continue

            cliente = cli_list[v_plan["cli_idx"]]
            dias_atras = int(170 - (v_idx * 168 / 99))
            fecha_venta = ahora - timedelta(days=dias_atras, hours=9 + (v_idx % 10), minutes=(v_idx * 11) % 60)

            items_venta = []
            for prod_idx, cant in v_plan["lineas"]:
                prod = prod_list[prod_idx]
                prod.refresh_from_db()
                items_venta.append({
                    "producto": prod,
                    "cantidad": cant,
                })

            metodo = metodos_pago[v_idx % len(metodos_pago)]
            ref_pago = f"REF-{metodo[:3]}-{fecha_venta.strftime('%Y%m%d')}-{v_idx+1:03d}"

            venta = registrar_venta(
                cliente=cliente,
                items=items_venta,
                usuario=usuario,
                observaciones=f"{obs_identificador} - Atención en salón de exhibición.",
                metodo_pago=metodo,
                referencia_pago=ref_pago,
            )

            # Ajuste de fecha histórica
            Venta.objects.filter(pk=venta.pk).update(fecha=fecha_venta)
            Ingreso.objects.filter(venta=venta).update(fecha=fecha_venta)
            MovimientoProducto.objects.filter(venta=venta).update(fecha=fecha_venta)
            ventas_creadas += 1

            # Anulación de venta para las 6 seleccionadas
            if v_idx in indices_anuladas:
                fecha_anulacion = fecha_venta + timedelta(hours=random.randint(4, 36))
                venta_anulada = anular_venta(
                    venta,
                    usuario=usuario,
                    motivo="[DEMO] Cancelación solicitada por cliente antes de entrega por cambio de medidas de habitación.",
                )
                MovimientoProducto.objects.filter(
                    venta=venta_anulada,
                    tipo=MovimientoProducto.ENTRADA,
                ).update(fecha=fecha_anulacion)
                ventas_anuladas += 1

        # Consolidar totales finales de base de datos
        total_ingresos_validos = sum(
            v.total for v in Venta.objects.filter(estado=Venta.ESTADO_COMPLETADA)
        )

        return {
            "categorias_creadas": categorias_creadas,
            "categorias_totales": Categoria.objects.count(),
            "proveedores_creados": proveedores_creados,
            "proveedores_totales": Proveedor.objects.count(),
            "materiales_creados": materiales_creados,
            "materiales_totales": Material.objects.count(),
            "productos_creados": productos_creados,
            "productos_totales": Producto.objects.count(),
            "clientes_creados": clientes_creados,
            "clientes_totales": Cliente.objects.count(),
            "compras_creadas": compras_creadas,
            "compras_totales": Compra.objects.count(),
            "consumos_taller": consumos_creados,
            "ventas_creadas": ventas_creadas,
            "ventas_totales": Venta.objects.count(),
            "ventas_anuladas": ventas_anuladas,
            "total_ingresos": total_ingresos_validos,
            "productos_disponibles": Producto.objects.filter(stock__gt=0).count(),
            "productos_stock_bajo": Producto.objects.filter(stock__gt=0, stock__lte=models_stock_minimo()).count(),
            "productos_agotados": Producto.objects.filter(stock=0).count(),
            "materiales_agotados": Material.objects.filter(stock=0).count(),
        }

    def _generar_plan_ventas(self, num_prods, num_clis):
        """Genera un plan determinista de 100 ventas variadas."""
        random.seed(42)  # Garantiza reproducibilidad exacta
        plan = []

        # Catálogo por popularidad
        prods_alta_rotacion = [14, 15, 8, 9, 32, 34]  # Sillas, veladores, repisas
        prods_media_rotacion = [0, 2, 4, 7, 11, 16, 18, 23, 24, 28, 33]  # Camas, escritorios, mesas
        prods_baja_rotacion = [1, 3, 5, 6, 10, 12, 13, 17, 19, 20, 21, 22, 25, 26, 27, 29, 30, 31, 35]

        for i in range(100):
            cli_idx = i % num_clis
            lineas = []

            if i % 3 == 0:
                # Venta multilínea (2 productos)
                p1 = prods_alta_rotacion[i % len(prods_alta_rotacion)]
                p2 = prods_media_rotacion[(i * 3) % len(prods_media_rotacion)]
                c1 = 2 if p1 in (14, 15, 32) else 1
                c2 = 1
                lineas.append((p1, c1))
                lineas.append((p2, c2))
            elif i % 5 == 0:
                # Venta de producto exclusivo o bajo stock
                p = prods_baja_rotacion[i % len(prods_baja_rotacion)]
                lineas.append((p, 1))
            else:
                # Venta regular
                p = (prods_alta_rotacion if i % 2 == 0 else prods_media_rotacion)[i % 6]
                c = 4 if p in (14, 15) else (2 if p in (8, 9, 32) else 1)
                lineas.append((p, c))

            plan.append({
                "cli_idx": cli_idx,
                "lineas": lineas,
            })

        return plan

    def _imprimir_resumen(self, r, dry_run=False):
        etiqueta = "SIMULACIÓN (--dry-run)" if dry_run else "BASE DE DATOS"
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"RESUMEN DE REGISTROS [{etiqueta}]")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Categorías:             {r['categorias_totales']} (nuevas: {r['categorias_creadas']})")
        self.stdout.write(f"Proveedores:            {r['proveedores_totales']} (nuevos: {r['proveedores_creados']})")
        self.stdout.write(f"Materiales:             {r['materiales_totales']} (nuevos: {r['materiales_creados']})")
        self.stdout.write(f"Productos:              {r['productos_totales']} (nuevos: {r['productos_creados']})")
        self.stdout.write(f"Clientes:               {r['clientes_totales']} (nuevos: {r['clientes_creados']})")
        self.stdout.write(f"Compras registradas:    {r['compras_totales']} (nuevas: {r['compras_creadas']})")
        self.stdout.write(f"Consumos en taller:     {r['consumos_taller']}")
        self.stdout.write(f"Ventas registradas:     {r['ventas_totales']} (nuevas: {r['ventas_creadas']})")
        self.stdout.write(f"Ventas anuladas (audit):{r['ventas_anuladas']}")
        self.stdout.write(f"Total Ingresos (Bs):    Bs {r['total_ingresos']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        self.stdout.write(f"\nESTADO DEL INVENTARIO:")
        self.stdout.write(f"- Productos disponibles: {r['productos_disponibles']}")
        self.stdout.write(f"- Productos stock bajo:  {r['productos_stock_bajo']}")
        self.stdout.write(f"- Productos agotados:    {r['productos_agotados']}")
        self.stdout.write(f"- Materiales agotados:   {r['materiales_agotados']}")
        self.stdout.write(f"{'='*60}\n")


def models_stock_minimo():
    from django.db.models import F
    return F("stock_minimo")
