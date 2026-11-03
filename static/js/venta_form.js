(function () {
    "use strict";

    const form = document.getElementById("venta-form");

    if (!form) {
        return;
    }

    const body = document.getElementById("sale-lines-body");
    const addButton = document.getElementById("add-line");
    const totalElement = document.getElementById("sale-total");
    const totalFormsInput = form.querySelector(
        'input[name="detalle-TOTAL_FORMS"]'
    );
    const dataElement = document.getElementById("productos-datos");
    const template = document.getElementById("empty-form-template");

    if (!body || !addButton || !totalElement || !totalFormsInput) {
        return;
    }

    const productos = dataElement
        ? JSON.parse(dataElement.textContent)
        : {};

    const formatoMoneda = (valor) => (
        "Bs " + Number(valor || 0).toFixed(2)
    );

    const obtenerDelete = (fila) => (
        fila.querySelector('input[name$="-DELETE"]')
    );

    const actualizarFila = (fila) => {
        const select = fila.querySelector(".producto-select");
        const cantidad = fila.querySelector(".cantidad-input");
        const celdaStock = fila.querySelector(".stock-cell");
        const celdaPrecio = fila.querySelector(".price-cell");
        const celdaSubtotal = fila.querySelector(".subtotal-cell");
        const deleteCheckbox = obtenerDelete(fila);

        if (deleteCheckbox && deleteCheckbox.checked) {
            fila.classList.add("row-hidden");
        } else {
            fila.classList.remove("row-hidden");
        }

        const info = (
            select && select.value
                ? productos[select.value]
                : null
        );

        if (celdaStock) {
            celdaStock.textContent = info ? info.stock : "—";
        }

        const precio = info ? Number(info.precio) : 0;
        const unidades = cantidad
            ? Math.max(0, parseInt(cantidad.value, 10) || 0)
            : 0;

        if (cantidad && info) {
            cantidad.max = info.stock;
        }

        if (celdaPrecio) {
            celdaPrecio.textContent = formatoMoneda(precio);
        }

        if (celdaSubtotal) {
            celdaSubtotal.textContent = formatoMoneda(
                precio * unidades
            );
        }

        actualizarTotal();
    };

    const actualizarTotal = () => {
        let total = 0;

        body.querySelectorAll(".sale-row").forEach((fila) => {
            const deleteCheckbox = obtenerDelete(fila);

            if (deleteCheckbox && deleteCheckbox.checked) {
                return;
            }

            const select = fila.querySelector(".producto-select");
            const cantidad = fila.querySelector(".cantidad-input");
            const info = (
                select && select.value
                    ? productos[select.value]
                    : null
            );
            const precio = info ? Number(info.precio) : 0;
            const unidades = cantidad
                ? Math.max(0, parseInt(cantidad.value, 10) || 0)
                : 0;

            total += precio * unidades;
        });

        totalElement.textContent = formatoMoneda(total);
    };

    const vincularFila = (fila) => {
        fila.querySelectorAll(
            ".producto-select, .cantidad-input"
        ).forEach((campo) => {
            campo.addEventListener("change", () => actualizarFila(fila));
            campo.addEventListener("input", () => actualizarFila(fila));
        });

        const deleteCheckbox = obtenerDelete(fila);

        if (deleteCheckbox) {
            deleteCheckbox.addEventListener(
                "change",
                () => actualizarFila(fila)
            );
        }

        actualizarFila(fila);
    };

    body.querySelectorAll(".sale-row").forEach(vincularFila);

    addButton.addEventListener("click", () => {
        if (!template) {
            return;
        }

        const indice = parseInt(totalFormsInput.value, 10);

        if (Number.isNaN(indice)) {
            return;
        }

        const fila = template.content
            .firstElementChild
            .cloneNode(true);

        fila.innerHTML = fila.innerHTML.replaceAll(
            "__prefix__",
            String(indice)
        );

        body.appendChild(fila);
        totalFormsInput.value = String(indice + 1);

        vincularFila(fila);

        const select = fila.querySelector(".producto-select");

        if (select) {
            select.focus();
        }
    });

    form.addEventListener("submit", () => {
        const boton = document.getElementById("save-sale");

        if (boton) {
            boton.disabled = true;
            boton.textContent = "Registrando...";
        }
    });
})();
