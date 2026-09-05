# Lago web front (nginx serving the built single-page app), as the image's own nginx
# user (uid 101) instead of root (crew#623, same founder decision as lago-api.Dockerfile).
# Three things stop stock nginx running unprivileged, and this image changes exactly those:
#   1. it listens on 80, and a non-root process cannot bind below 1024 -- adding
#      NET_BIND_SERVICE in a securityContext does not reach a non-root process because the
#      kubelet grants no ambient capabilities, so the port moves to 8080 and lago.yaml moves
#      the Service targetPort and the probes with it;
#   2. it writes its pid to /run/nginx.pid, which is root-owned, so the pid moves to /tmp;
#   3. the image's entrypoint (.env.sh) rewrites env-config.js inside the html root at
#      start, so that root and nginx's own cache and log directories are handed to uid 101.
# The `user nginx;` directive is dropped: it is a no-op when the master already runs
# unprivileged and nginx logs a warning about it on every boot.
FROM docker.io/getlago/front:v1.33.4
RUN sed -i -e 's/listen 80;/listen 8080;/' -e 's/listen \[::\]:80;/listen [::]:8080;/' /etc/nginx/conf.d/default.conf \
    && sed -i -e '/^user  nginx;/d' -e 's#^pid .*#pid /tmp/nginx.pid;#' /etc/nginx/nginx.conf \
    && chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx
USER 101:101
EXPOSE 8080
