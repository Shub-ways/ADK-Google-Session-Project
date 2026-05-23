FROM nginx:alpine

# Install envsubst (part of gettext)
RUN apk add --no-cache gettext

# Copy the index.html as a template
COPY index.html /usr/share/nginx/html/index.template.html

# Create a startup script to replace the backend URL
RUN echo '#!/bin/sh' > /docker-entrypoint.d/40-substitute-env-vars.sh && \
    echo 'envsubst "\$BACKEND_URL" < /usr/share/nginx/html/index.template.html > /usr/share/nginx/html/index.html' >> /docker-entrypoint.d/40-substitute-env-vars.sh && \
    chmod +x /docker-entrypoint.d/40-substitute-env-vars.sh

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
