###############################################################################
# Stage 1: Build Java static-analysis module with Maven
###############################################################################
FROM maven:3.9-eclipse-temurin-17 AS java-builder

WORKDIR /build

COPY pom.xml .
COPY src/ src/
COPY input/api-jar/ input/api-jar/

RUN mvn clean package -DskipTests -q

###############################################################################
# Stage 2: Build React frontend
###############################################################################
FROM node:16-alpine AS frontend-builder

WORKDIR /build

COPY wwwreport/package.json .
RUN npm install --legacy-peer-deps 2>&1 | tail -5 \
    && npm install ajv@8 --legacy-peer-deps 2>&1 | tail -3

COPY wwwreport/ .
RUN npm run build

###############################################################################
# Stage 3: Runtime — Python 3.10 + Java 17 + JDK 8 + tools
###############################################################################
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# --- System packages ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    openjdk-8-jdk-headless \
    openjdk-17-jdk-headless \
    wget \
    curl \
    unzip \
    zip \
    git \
    sqlite3 \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# --- Java environment (detect architecture dynamically) ---
RUN ARCH=$(dpkg --print-architecture) && \
    echo "Detected architecture: ${ARCH}" && \
    ln -sf /usr/lib/jvm/java-17-openjdk-${ARCH} /opt/java-17 && \
    ln -sf /usr/lib/jvm/java-8-openjdk-${ARCH} /opt/java-8

ENV JAVA_HOME=/opt/java-17
ENV JDK8_HOME=/opt/java-8
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# --- Create Python virtual environment ---
RUN python3.10 -m venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# --- Download external tools ---
RUN mkdir -p /opt/tools/misc

# apktool
RUN wget -q -O /opt/tools/misc/apktool.jar \
    "https://github.com/iBotPeaches/Apktool/releases/download/v2.9.3/apktool_2.9.3.jar"

# APKEditor (REAndroid)
RUN wget -q -O /opt/tools/misc/APKEditor.jar \
    "https://github.com/REAndroid/APKEditor/releases/download/V1.4.7/APKEditor-1.4.7.jar"

# dex2jar
RUN wget -q -O /tmp/dex2jar.zip \
    "https://github.com/pxb1988/dex2jar/releases/download/v2.4/dex-tools-v2.4.zip" \
    && unzip -q /tmp/dex2jar.zip -d /opt/tools/misc/ \
    && mv /opt/tools/misc/dex-tools-v2.4 /opt/tools/misc/dex-tools \
    && chmod +x /opt/tools/misc/dex-tools/*.sh \
    && rm /tmp/dex2jar.zip

# Generate a debug signing key (PKCS8 .pk8 + X.509 .pem) for APK re-signing
RUN keytool -genkeypair \
    -alias instrumate \
    -keyalg RSA -keysize 2048 -validity 10000 \
    -keystore /tmp/debug.jks \
    -storepass android -keypass android \
    -dname "CN=InstruMate,OU=Research,O=InstruMate,L=Unknown,ST=Unknown,C=US" \
    && keytool -exportcert -alias instrumate \
    -keystore /tmp/debug.jks -storepass android \
    -rfc -file /opt/tools/misc/signkey.x509.pem \
    && keytool -importkeystore \
    -srckeystore /tmp/debug.jks -srcstorepass android -srcalias instrumate \
    -destkeystore /tmp/debug.p12 -deststoretype PKCS12 -deststorepass android \
    && openssl pkcs12 -in /tmp/debug.p12 -passin pass:android \
    -nodes -nocerts -out /opt/tools/misc/signkey.pk8 \
    && rm -f /tmp/debug.jks /tmp/debug.p12

# --- Install Python dependencies ---
WORKDIR /app

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt \
    && pip install --no-cache-dir --no-deps pyaxml==0.0.5

# --- Copy Java JAR from build stage ---
COPY --from=java-builder /build/target/static-analysis-module-0.0.1-SNAPSHOT.jar /opt/java-jar/

# --- Copy frontend build from build stage ---
COPY --from=frontend-builder /build/build/ /opt/wwwreport-build/

# --- Copy project source ---
COPY pymate/ pymate/
COPY api/ api/
COPY input/ input/
COPY start.py .
COPY forensic-mate.py .
COPY entrypoint.sh .
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# --- Environment ---
ENV INSTRUMATE_OUTPUT_DIR=/data/output
ENV INSTRUMATE_TMP_DIR=/data/tmp
ENV INSTRUMATE_UPLOAD_DIR=/data/uploads
ENV INSTRUMATE_TOOLS_DIR=/opt/tools
ENV INSTRUMATE_INPUT_DIR=/app/input
ENV INSTRUMATE_WWWREPORT_DIR=/opt/wwwreport-build
ENV WORKERS=2
ENV LOG_LEVEL=info

RUN mkdir -p /data/output /data/tmp /data/uploads

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
