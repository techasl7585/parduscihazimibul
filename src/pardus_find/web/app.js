"use strict";

const state = {
  token: "",
  local: false,
  config: null,
  serverLocalIp: null,
  devices: [],
  selectedId: null,
  timer: null,
  map: null,
  positionMarker: null,
  accuracyCircle: null,
};

const elements = {
  connectionDot: document.querySelector("#connectionDot"),
  connectionText: document.querySelector("#connectionText"),
  onlineCount: document.querySelector("#onlineCount"),
  deviceCount: document.querySelector("#deviceCount"),
  refreshTime: document.querySelector("#refreshTime"),
  refreshButton: document.querySelector("#refreshButton"),
  deviceList: document.querySelector("#deviceList"),
  mapPlaceholder: document.querySelector("#mapPlaceholder"),
  mapView: document.querySelector("#mapView"),
  deviceDetail: document.querySelector("#deviceDetail"),
  detailStatus: document.querySelector("#detailStatus"),
  detailName: document.querySelector("#detailName"),
  detailLocation: document.querySelector("#detailLocation"),
  detailSeen: document.querySelector("#detailSeen"),
  detailSource: document.querySelector("#detailSource"),
  detailIp: document.querySelector("#detailIp"),
  openMapLink: document.querySelector("#openMapLink"),
  localTools: document.querySelector("#localTools"),
  viewerCode: document.querySelector("#viewerCode"),
  phoneUrl: document.querySelector("#phoneUrl"),
  preciseButton: document.querySelector("#preciseButton"),
  preciseMessage: document.querySelector("#preciseMessage"),
  settingsForm: document.querySelector("#settingsForm"),
  settingsMessage: document.querySelector("#settingsMessage"),
  deviceName: document.querySelector("#deviceName"),
  centerUrl: document.querySelector("#centerUrl"),
  organizationKey: document.querySelector("#organizationKey"),
  locationEnabled: document.querySelector("#locationEnabled"),
  loginModal: document.querySelector("#loginModal"),
  loginForm: document.querySelector("#loginForm"),
  loginCode: document.querySelector("#loginCode"),
  loginMessage: document.querySelector("#loginMessage"),
};

function authHeaders() {
  return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    cache: "no-store",
    ...options,
    headers: {
      ...authHeaders(),
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
  });
  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = { error: `Sunucu HTTP ${response.status} döndürdü` };
  }
  if (!response.ok) {
    const error = new Error(payload.error || payload.message || "İstek başarısız");
    error.status = response.status;
    throw error;
  }
  return payload;
}

function tokenFromHash() {
  const hash = new URLSearchParams(window.location.hash.slice(1));
  const code = hash.get("code") || hash.get("token");
  if (code) {
    window.history.replaceState(null, "", window.location.pathname);
    localStorage.setItem("pardus-find-token", code);
    return code;
  }
  return localStorage.getItem("pardus-find-token") || "";
}

function setConnection(online, text) {
  elements.connectionDot.className = `dot ${online ? "online" : "offline"}`;
  elements.connectionText.textContent = text;
}

function dateText(timestamp) {
  if (!timestamp) return "Bilinmiyor";
  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(timestamp * 1000));
}

function relativeText(timestamp) {
  if (!timestamp) return "Bilinmiyor";
  const seconds = Math.max(0, Math.round(Date.now() / 1000 - timestamp));
  if (seconds < 10) return "Şimdi";
  if (seconds < 60) return `${seconds} sn önce`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} dk önce`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} sa önce`;
  return dateText(timestamp);
}

function locationText(device) {
  const parts = [device.city, device.region, device.country].filter(Boolean);
  return parts.length ? [...new Set(parts)].join(", ") : "Koordinat mevcut";
}

function usableCoordinate(value, minimum, maximum) {
  if (value === null || value === undefined || value === "") return null;
  const number = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(number) || number < minimum || number > maximum) {
    return null;
  }
  return number;
}

function coordinatesFromDevice(device) {
  const latitude = usableCoordinate(device.latitude, -90, 90);
  const longitude = usableCoordinate(device.longitude, -180, 180);
  if (latitude === null || longitude === null) return null;
  if (latitude === 0 && longitude === 0) return null;
  return { latitude, longitude };
}

function setMapPlaceholder(title, message) {
  elements.mapPlaceholder.querySelector("h2").textContent = title;
  elements.mapPlaceholder.querySelector("p").textContent = message;
}

function hideMap() {
  elements.mapView.classList.remove("visible");
  elements.mapPlaceholder.classList.remove("hidden");
}

function showMap(latitude, longitude, accuracy) {
  if (typeof L === "undefined") {
    hideMap();
    setMapPlaceholder(
      "Harita yüklenemedi",
      "Sayfayı yenileyip yeniden deneyin.",
    );
    return;
  }

  elements.mapPlaceholder.classList.add("hidden");
  elements.mapView.classList.add("visible");

  if (!state.map) {
    state.map = L.map(elements.mapView, {
      zoomControl: true,
      attributionControl: true,
      preferCanvas: true,
    });
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      minZoom: 3,
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap katkıcıları",
    }).addTo(state.map);
  }

  const point = [latitude, longitude];
  const safeAccuracy = Math.max(10, Number(accuracy || 250));
  const zoom = safeAccuracy <= 100 ? 16 : safeAccuracy <= 1000 ? 14 : 11;
  state.map.setView(point, zoom, { animate: true });

  if (!state.positionMarker) {
    state.positionMarker = L.circleMarker(point, {
      radius: 10,
      color: "#d9fffb",
      weight: 3,
      fillColor: "#21cfc4",
      fillOpacity: 1,
    }).addTo(state.map);
  } else {
    state.positionMarker.setLatLng(point);
  }

  if (!state.accuracyCircle) {
    state.accuracyCircle = L.circle(point, {
      radius: safeAccuracy,
      color: "#31d5cb",
      weight: 1,
      opacity: 0.75,
      fillColor: "#31d5cb",
      fillOpacity: 0.13,
    }).addTo(state.map);
  } else {
    state.accuracyCircle.setLatLng(point);
    state.accuracyCircle.setRadius(safeAccuracy);
  }

  window.setTimeout(() => state.map?.invalidateSize(), 80);
}

function renderDevices() {
  const online = state.devices.filter((device) => device.online).length;
  elements.onlineCount.textContent = String(online);
  elements.deviceCount.textContent = String(state.devices.length);
  elements.refreshTime.textContent = new Intl.DateTimeFormat("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date());

  if (!state.devices.length) {
    elements.deviceList.innerHTML =
      '<div class="empty-state">Henüz konum gönderen bir cihaz bulunmuyor.</div>';
    state.selectedId = null;
    renderSelected();
    return;
  }

  if (!state.selectedId || !state.devices.some((d) => d.device_id === state.selectedId)) {
    state.selectedId = state.devices[0].device_id;
  }

  elements.deviceList.replaceChildren(
    ...state.devices.map((device) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `device-button ${
        state.selectedId === device.device_id ? "active" : ""
      }`;
      const icon = document.createElement("span");
      icon.className = "device-icon";
      icon.textContent = "⌁";
      const copy = document.createElement("span");
      const name = document.createElement("strong");
      name.textContent = device.device_name;
      const seen = document.createElement("small");
      seen.textContent = device.online ? "Şu anda açık" : relativeText(device.last_seen);
      copy.append(name, seen);
      const status = document.createElement("span");
      status.className = `device-state ${device.online ? "online" : ""}`;
      button.append(icon, copy, status);
      button.addEventListener("click", () => {
        state.selectedId = device.device_id;
        renderDevices();
      });
      return button;
    }),
  );
  renderSelected();
}

function renderSelected() {
  const device = state.devices.find((item) => item.device_id === state.selectedId);
  if (!device) {
    hideMap();
    elements.deviceDetail.classList.add("hidden");
    return;
  }

  elements.deviceDetail.classList.remove("hidden");
  elements.detailStatus.className = `status-pill ${device.online ? "online" : ""}`;
  elements.detailStatus.textContent = device.online ? "ÇEVRİM İÇİ" : "ÇEVRİM DIŞI";
  elements.detailName.textContent = device.device_name;
  elements.detailSeen.textContent = relativeText(device.last_seen);
  elements.detailSource.textContent =
    device.location_source === "browser"
      ? "Tarayıcı konumu"
      : device.location_source === "pardus-location"
        ? "Pardus Konum Servisi"
        : device.location_source === "pardus-positon"
          ? "Bilgisayar Wi-Fi konumu"
          : device.location_source === "pardus-wifi"
            ? "Wi-Fi konumu (BeaconDB)"
            : device.location_source === "pardus-network"
              ? "Yaklaşık ağ konumu"
        : device.location_source === "ip"
          ? "Yaklaşık IP konumu"
          : "Henüz alınmadı";
  elements.detailIp.textContent = device.local_ip || "Bilinmiyor";

  const coordinates = coordinatesFromDevice(device);
  if (!coordinates) {
    elements.detailLocation.textContent = "Konum bekleniyor";
    hideMap();
    setMapPlaceholder(
      "Konum henüz alınamadı",
      "Pardus Konum Servisi geçerli bir konum gönderdiğinde harita burada görünecek.",
    );
    elements.openMapLink.classList.add("hidden");
    return;
  }

  const { latitude, longitude } = coordinates;
  showMap(latitude, longitude, device.accuracy_m);
  elements.detailLocation.textContent = locationText(device);
  elements.openMapLink.href =
    `https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=15/${latitude}/${longitude}`;
  elements.openMapLink.classList.remove("hidden");
}

async function loadDevices() {
  try {
    const payload = await api("/api/devices");
    state.devices = payload.devices || [];
    renderDevices();
    setConnection(true, "Merkeze bağlı");
  } catch (error) {
    if (error.status === 401) {
      localStorage.removeItem("pardus-find-token");
      state.token = "";
      elements.loginModal.classList.remove("hidden");
    }
    setConnection(false, "Merkeze ulaşılamıyor");
  }
}

function configureLocalTools() {
  if (!state.local) return;
  elements.localTools.classList.remove("hidden");
  elements.viewerCode.textContent = state.config.viewer_code || "—";
  elements.deviceName.value = state.config.device_name || "";
  elements.centerUrl.value = state.config.center_url || "";
  elements.organizationKey.value = state.config.organization_key || "";
  elements.locationEnabled.checked = Boolean(state.config.location_enabled);
  state.token = state.config.admin_token || state.token;

  const currentDevice = state.devices.find(
    (device) => device.device_id === state.config.device_id,
  );
  const host =
    currentDevice?.local_ip || state.serverLocalIp || window.location.hostname;
  const port = window.location.port ? `:${window.location.port}` : "";
  const url = `${window.location.protocol}//${host}${port}/#code=${state.config.viewer_code}`;
  elements.phoneUrl.href = url;
  elements.phoneUrl.textContent = url.replace(/#code=.*/, "");
}

async function bootstrap() {
  state.token = tokenFromHash();
  try {
    const payload = await api("/api/bootstrap");
    state.local = Boolean(payload.local);
    state.config = payload.config;
    state.serverLocalIp = payload.server_local_ip || null;
    elements.loginModal.classList.add("hidden");
    await loadDevices();
    configureLocalTools();
    clearInterval(state.timer);
    state.timer = setInterval(loadDevices, 10_000);
  } catch (error) {
    if (error.status === 401) {
      elements.loginModal.classList.remove("hidden");
      setTimeout(() => elements.loginCode.focus(), 80);
    } else {
      setConnection(false, "Sunucu yanıt vermiyor");
    }
  }
}

elements.refreshButton.addEventListener("click", loadDevices);

elements.loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const code = elements.loginCode.value.trim();
  if (!/^\d{8}$/.test(code)) {
    elements.loginMessage.textContent = "8 haneli erişim kodunu girin.";
    return;
  }
  state.token = code;
  try {
    await api("/api/bootstrap");
    localStorage.setItem("pardus-find-token", code);
    elements.loginMessage.textContent = "";
    await bootstrap();
  } catch (_error) {
    state.token = "";
    elements.loginMessage.textContent = "Erişim kodu yanlış.";
  }
});

elements.preciseButton.addEventListener("click", () => {
  elements.preciseMessage.classList.remove("error");
  if (!navigator.geolocation) {
    elements.preciseMessage.classList.add("error");
    elements.preciseMessage.textContent = "Tarayıcı konum özelliğini desteklemiyor.";
    return;
  }
  elements.preciseMessage.textContent = "Konum izni bekleniyor…";
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      try {
        await api("/api/precise-location", {
          method: "POST",
          body: JSON.stringify({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
          }),
        });
        elements.preciseMessage.textContent = "Hassas konum merkeze gönderildi.";
        await loadDevices();
      } catch (error) {
        elements.preciseMessage.classList.add("error");
        elements.preciseMessage.textContent = error.message;
      }
    },
    (error) => {
      elements.preciseMessage.classList.add("error");
      elements.preciseMessage.textContent =
        error.code === error.PERMISSION_DENIED
          ? "Konum izni verilmedi."
          : "Konum alınamadı. Biraz sonra yeniden deneyin.";
    },
    { enableHighAccuracy: true, timeout: 15_000, maximumAge: 60_000 },
  );
});

elements.settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  elements.settingsMessage.classList.remove("error");
  elements.settingsMessage.textContent = "Kaydediliyor…";
  try {
    const payload = await api("/api/settings", {
      method: "POST",
      body: JSON.stringify({
        device_name: elements.deviceName.value,
        center_url: elements.centerUrl.value,
        organization_key: elements.organizationKey.value,
        location_enabled: elements.locationEnabled.checked,
      }),
    });
    state.config = { ...state.config, ...payload.config };
    elements.settingsMessage.textContent = "Ayarlar kaydedildi.";
    setTimeout(loadDevices, 500);
  } catch (error) {
    elements.settingsMessage.classList.add("error");
    elements.settingsMessage.textContent = error.message;
  }
});

bootstrap();
