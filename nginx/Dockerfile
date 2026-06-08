# =============================================================================
# Container 2: Nginx come web server statico + reverse proxy verso il backend.
# =============================================================================
FROM nginx:1.27-alpine

# Configurazione del server (static + proxy /api).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Frontend statico (Vanilla JS/HTML/CSS).
#COPY frontend /usr/share/nginx/html # Ora montato dinamicamente come volume

EXPOSE 80
