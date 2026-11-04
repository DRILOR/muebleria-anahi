"""Descarga imágenes Unsplash ilustrativas asociadas por código estable de producto.

Nunca reemplaza una fotografía que ya esté asociada a un producto.
"""

from io import BytesIO
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from PIL import Image, ImageOps, UnidentifiedImageError

from inventario.models import Producto


# El identificador del producto es su código de negocio, no su posición en una lista.
PRODUCT_IMAGES = {
    "PRD-DOR-001": "bedroom_modern",
    "PRD-DOR-002": "bedroom_modern",
    "PRD-DOR-003": "bedroom_antique",
    "PRD-DOR-004": "bunk_bed",
    "PRD-DOR-005": "bedroom_wardrobe",
    "PRD-DOR-006": "bedroom_antique",
    "PRD-DOR-007": "bedroom_wardrobe",
    "PRD-DOR-008": "dresser",
    "PRD-DOR-009": "nightstand",
    "PRD-DOR-010": "nightstand_alt",
    "PRD-DOR-011": "bedroom_modern",
    "PRD-SAL-001": "dining_six",
    "PRD-SAL-002": "dining_six_alt",
    "PRD-SAL-003": "dining_round",
    "PRD-SAL-004": "wood_chair",
    "PRD-SAL-005": "dining_six",
    "PRD-SAL-006": "coffee_table",
    "PRD-SAL-007": "coffee_table_alt",
    "PRD-SAL-008": "tv_stand",
    "PRD-SAL-009": "tv_panel",
    "PRD-SAL-010": "dresser",
    "PRD-SAL-011": "glass_display",
    "PRD-OFI-001": "office_desk",
    "PRD-OFI-002": "office_desk_alt",
    "PRD-OFI-003": "office_shelves",
    "PRD-OFI-004": "bookshelf",
    "PRD-OFI-005": "bookshelf",
    "PRD-OFI-006": "dresser",
    "PRD-COC-001": "kitchen_wood",
    "PRD-COC-002": "kitchen_wood_alt",
    "PRD-COC-003": "kitchen_wood",
    "PRD-COC-004": "kitchen_wood_alt",
    "PRD-AUX-001": "bookshelf",
    "PRD-AUX-002": "shoe_rack",
    "PRD-AUX-003": "coat_rack",
    "PRD-AUX-004": "wood_chest",
}


IMAGE_SOURCES = {
    "bedroom_modern": ("https://images.unsplash.com/photo-1758072328635-586f3c121af2", "Clay Banks", "https://unsplash.com/photos/a-neutral-bedroom-with-a-large-bed-and-wooden-wardrobe-Xbe5BfScmvM"),
    "bedroom_antique": ("https://images.unsplash.com/photo-1775595224321-1d6290c0af02", "Jessica Martins", "https://unsplash.com/photos/bedroom-with-antique-wooden-wardrobe-and-bed-7br6nacKFvk"),
    "bedroom_wardrobe": ("https://images.unsplash.com/photo-1784653549444-b5d61634d05a", "McFollis", "https://unsplash.com/photos/modern-bedroom-with-a-large-bed-and-light-wooden-wardrobes-qvBvGBsSIwE"),
    "dresser": ("https://images.unsplash.com/photo-1718875728087-5ca86e8afb94", "George Pagan III", "https://unsplash.com/photos/a-large-wooden-dresser-with-many-drawers-_ronF_aZLx8"),
    "nightstand": ("https://images.unsplash.com/photo-1517912200034-4b768a55b0f3", "Annie Spratt", "https://unsplash.com/photos/brown-wooden-nightstand-beside-bed-XSdHnR_LJmE"),
    "nightstand_alt": ("https://images.unsplash.com/photo-1774578342062-cb222a06404b", "Franco Debartolo", "https://unsplash.com/photos/a-wooden-nightstand-with-a-lamp-and-plant-r_QmGmu_w18"),
    "dining_six": ("https://images.unsplash.com/photo-1758977404683-d04c315a005b", "Costa Live", "https://unsplash.com/photos/wooden-dining-table-with-six-chairs-in-a-bright-room-bkLo8CIIAnM"),
    "dining_six_alt": ("https://images.unsplash.com/photo-1758977404499-32e2cae3c846", "Costa Live", "https://unsplash.com/photos/modern-dining-room-with-wooden-chairs-and-table-AG81hQM0rXw"),
    "dining_round": ("https://images.unsplash.com/photo-1758243488349-2f37274e06e1", "Mathias Reding", "https://unsplash.com/photos/round-wooden-table-set-for-four-people-TC5Oso6aVaI"),
    "wood_chair": ("https://images.unsplash.com/photo-1642688528647-9dfafccdc8e8", "Clay Banks", "https://unsplash.com/photos/a-wooden-chair-sitting-on-top-of-a-hard-wood-floor-eiUqciHhfYs"),
    "coffee_table": ("https://images.unsplash.com/photo-1551706768-712aee5486b4", "Randy Fath", "https://unsplash.com/photos/rectangular-brown-wooden-coffee-table-beside-brown-sofa-zwoC3l3kMek"),
    "coffee_table_alt": ("https://images.unsplash.com/photo-1605475161596-c8ded579e67a", "Andrea Davis", "https://unsplash.com/photos/brown-wooden-coffee-table-beside-blue-couch-hfCS5un07f8"),
    "office_desk": ("https://images.unsplash.com/photo-1705417272217-490f4511abeb", "Marko Lengyel", "https://unsplash.com/photos/a-wooden-desk-topped-with-a-laptop-computer-ABuqkAcwlEs"),
    "office_desk_alt": ("https://images.unsplash.com/photo-1790270691715-a4034557b671", "Annie Spratt", "https://unsplash.com/photos/wooden-desk-and-chair-in-workspace-m8N-vHYb_fc"),
    "office_shelves": ("https://images.unsplash.com/photo-1772475385509-93fd87a2d4ba", "Caroline Badran", "https://unsplash.com/photos/modern-office-with-wooden-desk-and-shelves-ePhpXlJ6H2g"),
    "bookshelf": ("https://images.unsplash.com/photo-1758279746549-d24f3784879d", "Annie Spratt", "https://unsplash.com/photos/wooden-bookshelf-filled-with-books-and-decorative-items-2K7NmB22Awk"),
    "kitchen_wood": ("https://images.unsplash.com/photo-1678194332107-f83717499bf9", "Sebastian Graser", "https://unsplash.com/photos/a-kitchen-with-a-center-island-and-a-refrigerator-nvCIWCPuCjQ"),
    "kitchen_wood_alt": ("https://images.unsplash.com/photo-1678194332099-86f6a219f7b2", "Sebastian Graser", "https://unsplash.com/photos/a-kitchen-with-wooden-cabinets-and-a-stainless-steel-refrigerator-baVYzWPbk5I"),
    "bunk_bed": ("https://images.unsplash.com/photo-1722248214881-9bc53768965b", "Lisa Anna", "https://unsplash.com/photos/a-bedroom-with-a-bunk-bed-and-a-desk-bjJP4WMT4Kk"),
    "shoe_rack": ("https://images.unsplash.com/photo-1515231073646-9eb684da63d9", "Manki Kim", "https://unsplash.com/photos/brown-wooden-shoe-rack-A6OrNCnbc2M"),
    "coat_rack": ("https://images.unsplash.com/photo-1785185219165-5864bed2ec8a", "Paolo Bici", "https://unsplash.com/photos/modern-wooden-coat-rack-with-black-hooks-z7xoUoQs2hE"),
    "glass_display": ("https://images.unsplash.com/photo-1547296018-94c23dda0de1", "MF Evelyn", "https://unsplash.com/photos/white-wooden-framed-glass-display-cabinet-tlhkw3S3_1Y"),
    "wood_chest": ("https://images.unsplash.com/photo-1641359255145-9af4ff37a4f5", "Ray Shrewsberry", "https://unsplash.com/photos/a-wooden-box-sitting-on-top-of-a-wooden-table-jSC4TD9pKq0"),
    "tv_stand": ("https://images.unsplash.com/photo-1698674388698-f22228a79879", "JALG TV Stand", "https://unsplash.com/photos/a-television-sitting-on-top-of-a-wooden-stand-pVVJcs6hYR0"),
    "tv_panel": ("https://images.unsplash.com/photo-1759735218086-67f9f853ab8b", "Puscas Adryan", "https://unsplash.com/photos/modern-living-room-with-sofa-tv-and-artwork-ykgcjx46Z0o"),
}


def optimized_webp(url):
    request = Request(url + "?auto=format&fit=crop&w=1400&h=1100&q=82&fm=webp", headers={"User-Agent": "MuebleriaAnahi-DemoCatalog/1.0"})
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read(12 * 1024 * 1024 + 1)
    except (URLError, TimeoutError) as error:
        raise CommandError(f"No se pudo descargar una imagen de Unsplash: {error}") from error
    if len(payload) > 12 * 1024 * 1024:
        raise CommandError("La imagen remota supera el límite temporal de 12 MB.")
    try:
        with Image.open(BytesIO(payload)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((1400, 1100), Image.Resampling.LANCZOS)
            result = BytesIO()
            image.save(result, format="WEBP", quality=82, method=6)
            return result.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise CommandError("Unsplash devolvió un archivo que Pillow no reconoce como imagen.") from error


class Command(BaseCommand):
    help = "Asocia imágenes ilustrativas de Unsplash por código de producto, sin reemplazar fotos existentes."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Lista asociaciones sin descargar ni modificar registros.")

    def handle(self, *args, **options):
        productos = {producto.codigo: producto for producto in Producto.objects.filter(codigo__in=PRODUCT_IMAGES)}
        asignados = omitidos = referencias = 0
        cache_imagenes = {}
        for codigo, fuente in PRODUCT_IMAGES.items():
            producto = productos.get(codigo)
            if producto is None:
                self.stdout.write(self.style.WARNING(f"No existe el código {codigo}; no se creó ningún producto."))
                continue
            if fuente is None:
                referencias += 1
                continue
            if producto.imagen:
                omitidos += 1
                continue
            creador, pagina_fuente = IMAGE_SOURCES[fuente][1:]
            if options["dry_run"]:
                self.stdout.write(f"{codigo} → {fuente} ({creador}; {pagina_fuente})")
                continue
            if fuente not in cache_imagenes:
                cache_imagenes[fuente] = optimized_webp(IMAGE_SOURCES[fuente][0])
            producto.imagen.save(f"{codigo.lower()}.webp", ContentFile(cache_imagenes[fuente]), save=False)
            producto.save(update_fields=["imagen"])
            asignados += 1
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Simulación completa: no se descargaron archivos ni se modificó la base de datos."))
            return
        self.stdout.write(self.style.SUCCESS(f"Imágenes asociadas: {asignados}; fotografías existentes preservadas: {omitidos}; sin fuente específica (queda ilustración): {referencias}."))
