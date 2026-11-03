(function () {
    "use strict";

    const formulario = document.getElementById("chat-form");

    if (!formulario) {
        return;
    }

    const entrada = document.getElementById("chat-input");
    const mensajes = document.getElementById("chat-mensajes");
    const sugerencias = document.getElementById("chat-sugerencias");
    const boton = document.getElementById("chat-enviar");
    const token = formulario.querySelector(
        "[name='csrfmiddlewaretoken']"
    );
    let enviando = false;

    function crearMensaje(autor, texto, tipo) {
        const contenedor = document.createElement("div");
        contenedor.className = `chat-message ${tipo}`;

        const etiqueta = document.createElement("span");
        etiqueta.className = "chat-author";
        etiqueta.textContent = autor;

        const burbuja = document.createElement("div");
        burbuja.className = "chat-bubble";
        burbuja.textContent = texto;

        contenedor.append(etiqueta, burbuja);
        mensajes.appendChild(contenedor);
        mensajes.scrollTop = mensajes.scrollHeight;

        return contenedor;
    }

    function mostrarSugerencias(lista) {
        sugerencias.replaceChildren();

        if (!Array.isArray(lista)) {
            return;
        }

        lista.forEach(function (texto) {
            if (typeof texto !== "string" || !texto.trim()) {
                return;
            }

            const botonSugerencia = document.createElement("button");
            botonSugerencia.type = "button";
            botonSugerencia.className = "chat-chip";
            botonSugerencia.dataset.sugerencia = texto;
            botonSugerencia.textContent = texto;
            sugerencias.appendChild(botonSugerencia);
        });
    }

    function ajustarAltura() {
        entrada.style.height = "auto";
        entrada.style.height = `${Math.min(entrada.scrollHeight, 140)}px`;
    }

    async function enviar(texto) {
        const consulta = texto.trim();

        if (!consulta || enviando) {
            return;
        }

        enviando = true;
        boton.disabled = true;
        entrada.value = "";
        ajustarAltura();

        crearMensaje("Tú", consulta, "user");

        const indicador = crearMensaje(
            "AnahíBot",
            "Consultando datos reales…",
            "bot pendiente"
        );

        try {
            const respuesta = await fetch(formulario.dataset.url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": token ? token.value : "",
                },
                body: JSON.stringify({ mensaje: consulta }),
            });

            const datos = await respuesta.json().catch(function () {
                return {};
            });

            indicador.remove();

            if (!respuesta.ok) {
                crearMensaje(
                    "AnahíBot",
                    datos.error || "No pude procesar la consulta.",
                    "bot error"
                );
                return;
            }

            crearMensaje("AnahíBot", datos.respuesta, "bot");
            mostrarSugerencias(datos.sugerencias);
        } catch (error) {
            indicador.remove();
            crearMensaje(
                "AnahíBot",
                "No se pudo conectar con el servidor. Intenta nuevamente.",
                "bot error"
            );
        } finally {
            enviando = false;
            boton.disabled = false;
            entrada.focus();
        }
    }

    formulario.addEventListener("submit", function (evento) {
        evento.preventDefault();
        enviar(entrada.value);
    });

    sugerencias.addEventListener("click", function (evento) {
        const chip = evento.target.closest("[data-sugerencia]");

        if (chip) {
            enviar(chip.dataset.sugerencia || "");
        }
    });

    entrada.addEventListener("input", ajustarAltura);

    entrada.addEventListener("keydown", function (evento) {
        if (evento.key === "Enter" && !evento.shiftKey) {
            evento.preventDefault();
            formulario.requestSubmit();
        }
    });

    ajustarAltura();
})();
