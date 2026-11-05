from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from inventario.models import Producto
from inventario.management.commands.cargar_imagenes_demo import optimized_webp


CATALOGO_IMAGES = {'PRD-DOR-001': {'url': 'https://images.unsplash.com/photo-1631048499455-4f9e26f23b9f',
                 'nombre': 'Cama matrimonial 2 plazas',
                 'autor': 'Point3D Commercial Imaging Ltd.',
                 'fuente': 'https://unsplash.com/photos/brown-wooden-bed-frame-with-white-bed-mattress-1dJfljc2tBk'},
 'PRD-DOR-002': {'url': 'https://images.unsplash.com/photo-1616594039964-ae9021a400a0',
                 'nombre': 'Cama King Size con cabecera acolchada',
                 'autor': 'Spacejoy',
                 'fuente': 'https://unsplash.com/photos/modern-bedroom-with-white-upholstered-bed-RUvW1KGD9a4'},
 'PRD-DOR-003': {'url': 'https://images.unsplash.com/photo-1775595224323-94a84b9be802',
                 'nombre': 'Cama plaza y media juvenil',
                 'autor': 'Jessica Martins',
                 'fuente': 'https://unsplash.com/photos/a-simple-bedroom-with-a-single-bed-and-wooden-furniture-zq3NlBqPTGA'},
 'PRD-DOR-004': {'url': 'https://images.unsplash.com/photo-1723258343563-7d71a55d6dfa',
                 'nombre': 'Cama cucheta / litera desmontable',
                 'autor': 'Alex Tyson',
                 'fuente': 'https://unsplash.com/photos/a-bedroom-with-bunk-beds-and-a-couch-ooxQsJEKqwU'},
 'PRD-DOR-005': {'url': 'https://images.unsplash.com/photo-1718939045285-b67f9e9f9f8b',
                 'nombre': 'Ropero 3 puertas con cajonería',
                 'autor': 'Michael Lock',
                 'fuente': 'https://unsplash.com/photos/a-closet-with-a-mirror-and-a-coat-rack-xYW0evnOOIY'},
 'PRD-DOR-006': {'url': 'https://images.unsplash.com/photo-1722650364570-90bf509d7dff',
                 'nombre': 'Ropero 4 puertas con espejo central',
                 'autor': 'Alex Tyson',
                 'fuente': 'https://unsplash.com/photos/a-bedroom-with-a-bed-mirror-and-closet-M6T7PXLjDQo'},
 'PRD-DOR-007': {'url': 'https://images.unsplash.com/photo-1784653549444-b5d61634d05a',
                 'nombre': 'Ropero empotrado modular de melamina',
                 'autor': 'McFollis',
                 'fuente': 'https://unsplash.com/photos/modern-bedroom-with-a-large-bed-and-light-wooden-wardrobes-qvBvGBsSIwE'},
 'PRD-DOR-008': {'url': 'https://images.unsplash.com/photo-1771039753521-fad683e5e091',
                 'nombre': 'Cómoda de 6 cajones',
                 'autor': 'Yx W',
                 'fuente': 'https://unsplash.com/photos/a-light-wood-dresser-with-three-drawers-M9utZq6lbPo'},
 'PRD-DOR-009': {'url': 'https://images.unsplash.com/photo-1517912200034-4b768a55b0f3',
                 'nombre': 'Mesa de noche de 2 cajones',
                 'autor': 'Annie Spratt',
                 'fuente': 'https://unsplash.com/photos/brown-wooden-nightstand-beside-bed-XSdHnR_LJmE'},
 'PRD-DOR-010': {'url': 'https://images.unsplash.com/photo-1779903726446-6f796d533d47',
                 'nombre': 'Mesa de noche minimalista melamina',
                 'autor': 'Caroline Badran',
                 'fuente': 'https://unsplash.com/photos/modern-bedroom-with-beige-bed-and-floating-white-nightstand-E-z8iE6LSgg'},
 'PRD-DOR-011': {'url': 'https://images.unsplash.com/photo-1720430498633-a8908d8706d1',
                 'nombre': 'Juego de dormitorio imperial',
                 'autor': 'Alex Tyson',
                 'fuente': 'https://unsplash.com/photos/a-bedroom-with-a-bed-dresser-and-mirror-17YnTgHkSEE'},
 'PRD-SAL-001': {'url': 'https://images.unsplash.com/photo-1758977403403-c51ef509e788',
                 'autor': 'Costa Live'},
 'PRD-SAL-002': {'url': 'https://images.unsplash.com/photo-1758977404499-32e2cae3c846',
                 'autor': 'Costa Live'},
 'PRD-SAL-003': {'url': 'https://images.unsplash.com/photo-1758243488349-2f37274e06e1',
                 'autor': 'Mathias Reding'},
 'PRD-SAL-004': {'url': 'https://images.unsplash.com/photo-1750306957114-ba6deb1eaa9f',
                 'autor': 'ObjectType RAW'},
 'PRD-SAL-005': {'url': 'https://images.unsplash.com/photo-1774468725355-bc7662ee1ef1',
                 'autor': 'Piotr AMS'},
 'PRD-SAL-006': {'url': 'https://images.unsplash.com/photo-1777513538143-8525eb3943f6',
                 'autor': 'Suryakant Prajapati'},
 'PRD-SAL-007': {'url': 'https://images.unsplash.com/photo-1748122601171-efbfa460ddc6',
                 'autor': 'Danny Greenberg'},
 'PRD-SAL-008': {'url': 'https://images.unsplash.com/photo-1698674388698-f22228a79879',
                 'autor': 'JALG TV Stand'},
 'PRD-SAL-009': {'url': 'https://images.unsplash.com/photo-1759735218086-67f9f853ab8b',
                 'autor': 'Puscas Adryan'},
 'PRD-SAL-010': {'url': 'https://images.unsplash.com/photo-1767963758785-b9def36c13e3',
                 'autor': 'Imani Bahati'},
 'PRD-SAL-011': {'url': 'https://images.unsplash.com/photo-1547296018-94c23dda0de1',
                 'autor': 'MF Evelyn'},
 'PRD-OFI-001': {'url': 'https://images.unsplash.com/photo-1681422480634-62baf0c7336e',
                 'autor': 'John Wayne Hill'},
 'PRD-OFI-002': {'url': 'https://images.unsplash.com/photo-1790270691715-a4034557b671',
                 'autor': 'Annie Spratt'},
 'PRD-OFI-003': {'url': 'https://images.unsplash.com/photo-1575318634028-6a0cfcb60c59',
                 'autor': 'Max Andrey'},
 'PRD-OFI-004': {'url': 'https://images.unsplash.com/photo-1758279746549-d24f3784879d',
                 'autor': 'Annie Spratt'},
 'PRD-OFI-005': {'url': 'https://images.unsplash.com/photo-1772475385509-93fd87a2d4ba',
                 'autor': 'Caroline Badran'},
 'PRD-OFI-006': {'url': 'https://images.unsplash.com/photo-1770869731843-bd36aa92403c',
                 'autor': 'Jéan Béller'},
 'PRD-COC-001': {'url': 'https://images.unsplash.com/photo-1723640584255-0a2850f65583',
                 'autor': 'Alex Tyson'},
 'PRD-COC-002': {'url': 'https://images.unsplash.com/photo-1609114215069-74764924d06b',
                 'autor': 'Nathan Dumlao'},
 'PRD-COC-003': {'url': 'https://images.unsplash.com/photo-1772475385491-f3cf64d4131a',
                 'autor': 'Caroline Badran'},
 'PRD-COC-004': {'url': 'https://images.unsplash.com/photo-1776950815445-f80f2b21fa50',
                 'autor': 'Alexander Mass'},
 'PRD-AUX-001': {'url': 'https://images.unsplash.com/photo-1529066745603-f368fa6d32de',
                 'autor': 'Annie Spratt'},
 'PRD-AUX-002': {'url': 'https://images.unsplash.com/photo-1515231073646-9eb684da63d9',
                 'autor': 'Manki Kim'},
 'PRD-AUX-003': {'url': 'https://images.unsplash.com/photo-1785185219165-5864bed2ec8a',
                 'autor': 'Paolo Bici'},
 'PRD-AUX-004': {'url': 'https://images.unsplash.com/photo-1641359255145-9af4ff37a4f5',
                 'autor': 'Ray Shrewsberry'}}


class Command(BaseCommand):
    help = (
        "Actualiza las fotografias referenciales del catalogo "
        "de Muebleria Anahi."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra asociaciones sin modificar imagenes.",
        )

    def handle(self, *args, **options):
        actualizados = 0
        fallidos = 0
        no_encontrados = 0

        for codigo, datos in CATALOGO_IMAGES.items():
            producto = Producto.objects.filter(
                codigo=codigo
            ).first()

            if producto is None:
                no_encontrados += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"{codigo}: producto no encontrado."
                    )
                )
                continue

            self.stdout.write(
                f"{codigo} | {producto.nombre}"
            )
            self.stdout.write(
                f"    Foto: {datos['autor']}"
            )

            if options["dry_run"]:
                continue

            try:
                contenido = optimized_webp(
                    datos["url"]
                )
            except CommandError as error:
                fallidos += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"    ERROR: {error}"
                    )
                )
                continue

            if producto.imagen:
                producto.imagen.delete(save=False)

            producto.imagen.save(
                f"{codigo.lower()}-v2.webp",
                ContentFile(contenido),
                save=False,
            )

            producto.save(
                update_fields=["imagen"]
            )
            actualizados += 1

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Simulacion terminada: "
                    f"{len(CATALOGO_IMAGES)} asociaciones."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Fotografias actualizadas: {actualizados}; "
                f"fallidas: {fallidos}; "
                f"productos no encontrados: {no_encontrados}."
            )
        )
