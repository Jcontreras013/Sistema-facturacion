(function () {
    "use strict";

    const DB_NAME = "mini-market-offline";
    const DB_VERSION = 2;
    const STORE_NAME = "pending_sales";
    const CONTINGENCY_STORE_NAME = "contingency_counter";
    const CONTINGENCY_KEY = "counter";
    const CHECKOUT_URL = "/ventas/pos/api/checkout/";

    if ("serviceWorker" in navigator) {
        window.addEventListener("load", () => {
            navigator.serviceWorker.register("/sw.js").catch((err) => {
                console.warn("No se pudo registrar el service worker:", err);
            });
        });
    }

    function getCookie(name) {
        const match = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
        return match ? decodeURIComponent(match.pop()) : "";
    }

    function openDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);
            request.onupgradeneeded = () => {
                const db = request.result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME, { keyPath: "localId", autoIncrement: true });
                }
                if (!db.objectStoreNames.contains(CONTINGENCY_STORE_NAME)) {
                    db.createObjectStore(CONTINGENCY_STORE_NAME, { keyPath: "key" });
                }
            };
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // ---- Contador local de contingencia (numeración de facturas sin internet) ----
    // Se guarda en este dispositivo el próximo correlativo a usar. Solo avanza hacia adelante:
    // nunca retrocede, aunque el valor del servidor sea menor (para nunca repetir un número ya
    // asignado localmente, incluso si la página se recarga estando todavía sin conexión).

    async function getContingencyState() {
        const db = await openDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(CONTINGENCY_STORE_NAME, "readonly");
            const store = tx.objectStore(CONTINGENCY_STORE_NAME);
            const req = store.get(CONTINGENCY_KEY);
            req.onsuccess = () => resolve(req.result || null);
            req.onerror = () => reject(req.error);
        });
    }

    async function setContingencyState(next) {
        const db = await openDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(CONTINGENCY_STORE_NAME, "readwrite");
            const store = tx.objectStore(CONTINGENCY_STORE_NAME);
            const req = store.put({ key: CONTINGENCY_KEY, next });
            req.onsuccess = () => resolve();
            req.onerror = () => reject(req.error);
        });
    }

    async function syncContingencyCounterFromServer(serverNext) {
        if (!serverNext) return;
        const state = await getContingencyState();
        if (!state || serverNext > state.next) {
            await setContingencyState(serverNext);
        }
    }

    async function reserveContingencyNumber(rangeEnd) {
        const state = await getContingencyState();
        const next = state ? state.next : null;
        if (!next || (rangeEnd && next > rangeEnd)) return null;
        await setContingencyState(next + 1);
        return next;
    }

    async function queueSale(payload) {
        const db = await openDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, "readwrite");
            const store = tx.objectStore(STORE_NAME);
            const record = { payload, createdAt: new Date().toISOString() };
            const req = store.add(record);
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    async function getPendingSales() {
        const db = await openDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, "readonly");
            const store = tx.objectStore(STORE_NAME);
            const req = store.getAll();
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    async function removePendingSale(localId) {
        const db = await openDB();
        return new Promise((resolve, reject) => {
            const tx = db.transaction(STORE_NAME, "readwrite");
            const store = tx.objectStore(STORE_NAME);
            const req = store.delete(localId);
            req.onsuccess = () => resolve();
            req.onerror = () => reject(req.error);
        });
    }

    async function countPendingSales() {
        const all = await getPendingSales();
        return all.length;
    }

    async function submitToServer(payload) {
        const response = await fetch(CHECKOUT_URL, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify(payload),
        });
        let data = null;
        try {
            data = await response.json();
        } catch (e) {
            data = null;
        }
        return { ok: response.ok && data && data.ok, status: response.status, data };
    }

    let syncing = false;

    async function syncPendingSales() {
        if (syncing || !navigator.onLine) return { synced: 0, remaining: await countPendingSales() };
        syncing = true;
        let synced = 0;
        try {
            const pending = await getPendingSales();
            for (const record of pending) {
                try {
                    const result = await submitToServer(record.payload);
                    if (result.ok) {
                        await removePendingSale(record.localId);
                        synced += 1;
                    } else if (result.status >= 400 && result.status < 500 && result.status !== 409) {
                        // Error de datos (no de conexión): no lo reintentamos indefinidamente para no bloquear la cola,
                        // pero lo dejamos guardado para revisión manual del administrador.
                        continue;
                    } else {
                        break;
                    }
                } catch (err) {
                    break; // Sin conexión real: paramos el barrido y reintentamos más tarde.
                }
            }
        } finally {
            syncing = false;
            updateBadge();
        }
        return { synced, remaining: await countPendingSales() };
    }

    let badgeEl = null;

    function ensureBadge() {
        if (badgeEl) return badgeEl;
        badgeEl = document.createElement("div");
        badgeEl.id = "mm-offline-badge";
        badgeEl.style.cssText =
            "position:fixed;bottom:12px;right:12px;z-index:2000;padding:6px 12px;border-radius:20px;" +
            "font-size:13px;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,.25);display:none;" +
            "font-family:-apple-system,'Segoe UI',Arial,sans-serif;color:#fff;";
        document.body.appendChild(badgeEl);
        return badgeEl;
    }

    async function updateBadge() {
        const el = ensureBadge();
        const pending = await countPendingSales();
        const online = navigator.onLine;

        if (online && pending === 0) {
            el.style.display = "none";
            return;
        }

        el.style.display = "block";
        if (!online) {
            el.style.background = "#dc3545";
            el.textContent = pending > 0
                ? `\u{1F534} Sin conexión · ${pending} venta(s) pendiente(s)`
                : "\u{1F534} Sin conexión";
        } else {
            el.style.background = "#fd7e14";
            el.textContent = `\u{1F7E0} Sincronizando ${pending} venta(s) pendiente(s)...`;
        }
    }

    window.addEventListener("online", () => {
        updateBadge();
        syncPendingSales();
    });
    window.addEventListener("offline", updateBadge);

    document.addEventListener("DOMContentLoaded", () => {
        updateBadge();
        if (navigator.onLine) {
            syncPendingSales();
        }
    });

    setInterval(() => {
        if (navigator.onLine) syncPendingSales();
    }, 20000);

    window.MMOffline = {
        queueSale,
        getPendingSales,
        removePendingSale,
        countPendingSales,
        submitToServer,
        syncPendingSales,
        updateBadge,
        getCookie,
        syncContingencyCounterFromServer,
        reserveContingencyNumber,
    };
})();
