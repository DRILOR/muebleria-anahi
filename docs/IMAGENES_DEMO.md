# Fotografías demostrativas del catálogo

Las fotos descargadas con `python manage.py cargar_imagenes_demo` son referencias visuales de Unsplash. No representan las piezas fabricadas ni se deben presentar como fotografías propias de Mueblería Anahí. El catálogo y el detalle las identifican como fotografías referenciales.

El comando asocia productos por código de inventario, optimiza cada archivo a WebP (máximo 1400 × 1100 px) y omite cualquier producto que ya tenga una imagen. Los códigos sin una coincidencia visual suficiente conservan la ilustración. Simula asociaciones sin descargar ni modificar datos con:

```bash
python manage.py cargar_imagenes_demo --dry-run
```

## Fuentes y autoría

Las páginas de las fotos indican que están disponibles bajo la licencia Unsplash. La [licencia oficial](https://unsplash.com/license) permite descarga, modificación y uso comercial sin atribución obligatoria; se enlazan las páginas de las fotos para dar crédito y trazabilidad.

| Tipo | Autor | Página de la foto | Códigos asociados |
|---|---|---|---|
| Dormitorio con cama y ropero | Clay Banks | [Unsplash](https://unsplash.com/photos/a-neutral-bedroom-with-a-large-bed-and-wooden-wardrobe-Xbe5BfScmvM) | DOR-001, DOR-002, DOR-011 |
| Dormitorio clásico | Jessica Martins | [Unsplash](https://unsplash.com/photos/bedroom-with-antique-wooden-wardrobe-and-bed-7br6nacKFvk) | DOR-003, DOR-006 |
| Dormitorio con roperos claros | McFollis | [Unsplash](https://unsplash.com/photos/modern-bedroom-with-a-large-bed-and-light-wooden-wardrobes-qvBvGBsSIwE) | DOR-005, DOR-007 |
| Cómoda / aparador / archivador con cajones | George Pagan III | [Unsplash](https://unsplash.com/photos/a-large-wooden-dresser-with-many-drawers-_ronF_aZLx8) | DOR-008, SAL-010, OFI-006 |
| Velador de madera | Annie Spratt | [Unsplash](https://unsplash.com/photos/brown-wooden-nightstand-beside-bed-XSdHnR_LJmE) | DOR-009 |
| Velador con lámpara | Franco Debartolo | [Unsplash](https://unsplash.com/photos/a-wooden-nightstand-with-a-lamp-and-plant-r_QmGmu_w18) | DOR-010 |
| Comedor de seis sillas | Costa Live | [Unsplash](https://unsplash.com/photos/wooden-dining-table-with-six-chairs-in-a-bright-room-bkLo8CIIAnM) | SAL-001, SAL-005 |
| Comedor de madera | Costa Live | [Unsplash](https://unsplash.com/photos/modern-dining-room-with-wooden-chairs-and-table-AG81hQM0rXw) | SAL-002 |
| Mesa redonda | Mathias Reding | [Unsplash](https://unsplash.com/photos/round-wooden-table-set-for-four-people-TC5Oso6aVaI) | SAL-003 |
| Silla de madera | Clay Banks | [Unsplash](https://unsplash.com/photos/a-wooden-chair-sitting-on-top-of-a-hard-wood-floor-eiUqciHhfYs) | SAL-004 |
| Mesa de centro | Randy Fath | [Unsplash](https://unsplash.com/photos/rectangular-brown-wooden-coffee-table-beside-brown-sofa-zwoC3l3kMek) | SAL-006 |
| Mesa de centro con sofá | Andrea Davis | [Unsplash](https://unsplash.com/photos/brown-wooden-coffee-table-beside-blue-couch-hfCS5un07f8) | SAL-007 |
| Escritorio de madera | Marko Lengyel | [Unsplash](https://unsplash.com/photos/a-wooden-desk-topped-with-a-laptop-computer-ABuqkAcwlEs) | OFI-001 |
| Escritorio y silla | Annie Spratt | [Unsplash](https://unsplash.com/photos/wooden-desk-and-chair-in-workspace-m8N-vHYb_fc) | OFI-002 |
| Oficina con repisas | Caroline Badran | [Unsplash](https://unsplash.com/photos/modern-office-with-wooden-desk-and-shelves-ePhpXlJ6H2g) | OFI-003 |
| Estantería de madera | Annie Spratt | [Unsplash](https://unsplash.com/photos/wooden-bookshelf-filled-with-books-and-decorative-items-2K7NmB22Awk) | OFI-004, OFI-005, AUX-001 |
| Cocina de madera | Sebastian Graser | [Unsplash](https://unsplash.com/photos/a-kitchen-with-a-center-island-and-a-refrigerator-nvCIWCPuCjQ) | COC-001, COC-003 |
| Cocina con gabinetes de madera | Sebastian Graser | [Unsplash](https://unsplash.com/photos/a-kitchen-with-wooden-cabinets-and-a-stainless-steel-refrigerator-baVYzWPbk5I) | COC-002, COC-004 |
| Litera | Lisa Anna | [Unsplash](https://unsplash.com/photos/a-bedroom-with-a-bunk-bed-and-a-desk-bjJP4WMT4Kk) | DOR-004 |
| Zapatera | Manki Kim | [Unsplash](https://unsplash.com/photos/brown-wooden-shoe-rack-A6OrNCnbc2M) | AUX-002 |
| Perchero de madera | Paolo Bici | [Unsplash](https://unsplash.com/photos/modern-wooden-coat-rack-with-black-hooks-z7xoUoQs2hE) | AUX-003 |
| Vitrina | MF Evelyn | [Unsplash](https://unsplash.com/photos/white-wooden-framed-glass-display-cabinet-tlhkw3S3_1Y) | SAL-011 |
| Baúl / caja de madera | Ray Shrewsberry | [Unsplash](https://unsplash.com/photos/a-wooden-box-sitting-on-top-of-a-wooden-table-jSC4TD9pKq0) | AUX-004 |
| Mueble de TV | JALG TV Stand | [Unsplash](https://unsplash.com/photos/a-television-sitting-on-top-of-a-wooden-stand-pVVJcs6hYR0) | SAL-008 |
| Panel de TV en ambiente | Puscas Adryan | [Unsplash](https://unsplash.com/photos/modern-living-room-with-sofa-tv-and-artwork-ykgcjx46Z0o) | SAL-009 |

Las fuentes se revisaron el 4 de noviembre de 2026. La asignación cubre los 36 códigos de demostración leídos de MySQL. Los registros que no forman parte de esos códigos y no tienen una fotografía propia conservan la ilustración claramente referencial.
