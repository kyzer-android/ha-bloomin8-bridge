ARG BUILD_FROM
FROM $BUILD_FROM

# - nodejs/npm       : runtime pour bloomin8_optimize.js
# - build-essential + libcairo2-dev + libpango1.0-dev + libjpeg-dev +
#   libgif-dev + librsvg2-dev : prérequis de compilation pour node-canvas
#   (dithering / rendu image utilisé par bloomin8_optimize.js)
# - cron             : planification person_to_album / bloomin8_optimize
# - jq               : lecture de /data/options.json dans run.sh
# - curl             : appels API HA / relance BLOOMIN8
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    build-essential \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    cron \
    jq \
    curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY app/package.json .
RUN npm install --omit=dev

COPY app/ .

COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
