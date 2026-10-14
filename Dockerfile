# reel-ai en un contenedor: Python + Node + FFmpeg + Chromium, sin instalar nada en tu maquina.
#
# Uso (desde la carpeta donde estan tus escenas):
#   macOS / Linux:  docker run --rm -v "$PWD:/work" ghcr.io/jesusfelipeb/reel-ai render mi-escena.json
#   Windows (PS):   docker run --rm -v "${PWD}:/work" ghcr.io/jesusfelipeb/reel-ai render mi-escena.json
#
# El codigo vive en /app; tu carpeta se monta en /work y ahi aparece output/.

FROM node:22-trixie-slim

# Python del sistema (3.13 en trixie) en un venv propio, y FFmpeg.
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv ffmpeg \
 && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN python3 -m venv "$VIRTUAL_ENV" \
 && pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

# --ignore-scripts saltea el postinstall (que bajaria Chromium completo). Se instala solo el
# headless shell, que es el que usa chromium.launch() sin cabeza: el mismo que se usa fuera
# de Docker, asi que los cuadros salen iguales. --with-deps trae las librerias y fuentes del
# sistema que Chromium necesita.
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund \
 && npx playwright install --with-deps --only-shell chromium \
 && chmod -R a+rX "$PLAYWRIGHT_BROWSERS_PATH" \
 && rm -rf /var/lib/apt/lists/* /root/.npm

COPY . .

# Tu carpeta: escenas, themes/, .env y output/ salen de aca, no de /app.
# Los ~900 cuadros intermedios de cada render quedan dentro del contenedor.
# HOME=/tmp permite correr con --user <tu uid> (Linux) sin un usuario creado en la imagen.
ENV REEL_PROJECT_DIR=/work \
    REEL_TMP_DIR=/tmp/reel \
    HOME=/tmp
WORKDIR /work

ENTRYPOINT ["python", "/app/reel.py"]
CMD ["--help"]
