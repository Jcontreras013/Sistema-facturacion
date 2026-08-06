{% load static %}
const CACHE_VERSION = "mini-market-v1";
const APP_SHELL_CACHE = CACHE_VERSION + "-shell";
const RUNTIME_CACHE = CACHE_VERSION + "-runtime";

const APP_SHELL_URLS = [
    "{% static 'vendor/bootstrap/css/bootstrap.min.css' %}",
    "{% static 'vendor/bootstrap/js/bootstrap.bundle.min.js' %}",
    "{% static 'vendor/bootstrap-icons/bootstrap-icons.min.css' %}",
    "{% static 'css/styles.css' %}",
    "{% static 'js/offline.js' %}",
    "{% static 'manifest.json' %}",
    "{% static 'icons/icon-192.png' %}",
    "{% static 'icons/icon-512.png' %}",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(APP_SHELL_CACHE).then((cache) => cache.addAll(APP_SHELL_URLS)).then(() => self.skipWaiting())
    );
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((names) =>
            Promise.all(
                names
                    .filter((name) => name.startsWith("mini-market-") && name !== APP_SHELL_CACHE && name !== RUNTIME_CACHE)
                    .map((name) => caches.delete(name))
            )
        ).then(() => self.clients.claim())
    );
});

function isStaticAsset(url) {
    return url.pathname.startsWith("/static/");
}

self.addEventListener("fetch", (event) => {
    const request = event.request;
    if (request.method !== "GET") {
        return;
    }
    const url = new URL(request.url);
    if (url.origin !== self.location.origin) {
        return;
    }
    if (url.pathname.startsWith("/admin/")) {
        return;
    }

    if (isStaticAsset(url)) {
        // Recursos estáticos: caché primero, red de respaldo.
        event.respondWith(
            caches.match(request).then((cached) => {
                if (cached) return cached;
                return fetch(request).then((response) => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(APP_SHELL_CACHE).then((cache) => cache.put(request, clone));
                    }
                    return response;
                });
            })
        );
        return;
    }

    // Páginas HTML: red primero (datos frescos), con respaldo en caché si no hay conexión.
    event.respondWith(
        fetch(request)
            .then((response) => {
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(RUNTIME_CACHE).then((cache) => cache.put(request, clone));
                }
                return response;
            })
            .catch(() => caches.match(request).then((cached) => cached || caches.match("/")))
    );
});
