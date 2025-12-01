const P2P_API_URL = "http://localhost:3000/api/nodes";
const GEOIP_URL = "http://ip-api.com/json/{ip}?fields=status,lat,lon";
const MAX_IPS = 800;
const UPDATE_INTERVAL = 10000;

let map;
let heatmapLayer;
let markersLayer;
let updateCount = 0;
let isUpdating = false;
let cachedLocations = [];
let ipToLocationCache = {};
let useDemoData = false;

function initMap() {
    const mapElement = document.getElementById('map');
    if (mapElement) {
        mapElement.style.width = window.innerWidth + 'px';
        mapElement.style.height = window.innerHeight + 'px';
    }
    
    map = L.map('map').setView([20, 0], 2);
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);
    
    markersLayer = L.layerGroup().addTo(map);
    heatmapLayer = L.heatLayer([], {
        radius: 30,
        blur: 40,
        maxZoom: 5,
        gradient: {
            0.2: 'blue',
            0.4: 'cyan',
            0.6: 'lime',
            0.8: 'yellow',
            1.0: 'red'
        }
    }).addTo(map);
    
    function forceFullScreen() {
        const mapElement = document.getElementById('map');
        const container = document.querySelector('.leaflet-container');
        
        if (mapElement) {
            mapElement.style.width = window.innerWidth + 'px';
            mapElement.style.height = window.innerHeight + 'px';
        }
        
        if (container) {
            container.style.width = window.innerWidth + 'px';
            container.style.height = window.innerHeight + 'px';
        }
        
        if (map) {
            map.invalidateSize(true);
        }
    }
    
    forceFullScreen();
    
    setTimeout(forceFullScreen, 10);
    setTimeout(forceFullScreen, 50);
    setTimeout(forceFullScreen, 100);
    setTimeout(forceFullScreen, 200);
    setTimeout(forceFullScreen, 500);
    setTimeout(forceFullScreen, 1000);
    
    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(forceFullScreen, 10);
    });
    
    window.addEventListener('load', forceFullScreen);
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', forceFullScreen);
    }
    
    fetchAndUpdate();
}

function isIPv4(host) {
    if (host.endsWith(".onion")) return false;
    if (host.startsWith("[")) return false;
    const parts = host.split(".");
    return parts.length === 4 && parts.every(part => !isNaN(parseInt(part)));
}

async function fetchSnapshotNodes() {
    try {
        updateStatus("Getting nodes from Bitcoin Core node...", "info");
        const response = await fetch(P2P_API_URL);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        const nodes = data.nodes || {};
        
        if (Object.keys(nodes).length > 0) {
            useDemoData = false;
            return nodes;
        }
    } catch (error) {
        console.warn("P2P discovery failed:", error);
        updateStatus("Bitcoin Core unavailable. Make sure bitcoind is running and server is running. Using demo data.", "warning");
    }
    
    updateStatus("Using demo data.", "warning");
    useDemoData = true;
    return generateDemoNodes();
}

function generateDemoNodes() {
    const demoNodes = {};
    const countries = [
        { name: "US", lat: 39.8283, lon: -98.5795, count: 150 },
        { name: "DE", lat: 51.1657, lon: 10.4515, count: 120 },
        { name: "GB", lat: 55.3781, lon: -3.4360, count: 80 },
        { name: "FR", lat: 46.2276, lon: 2.2137, count: 70 },
        { name: "CN", lat: 35.8617, lon: 104.1954, count: 60 },
        { name: "JP", lat: 36.2048, lon: 138.2529, count: 50 },
        { name: "CA", lat: 56.1304, lon: -106.3468, count: 40 },
        { name: "AU", lat: -25.2744, lon: 133.7751, count: 30 },
        { name: "BR", lat: -14.2350, lon: -51.9253, count: 25 },
        { name: "IN", lat: 20.5937, lon: 78.9629, count: 20 },
    ];
    
    let nodeCount = 0;
    countries.forEach(country => {
        for (let i = 0; i < country.count; i++) {
            const lat = country.lat + (Math.random() - 0.5) * 10;
            const lon = country.lon + (Math.random() - 0.5) * 10;
            const ip = generateRandomIP();
            demoNodes[`${ip}:8333`] = { version: "70015" };
            cachedLocations.push([lat, lon]);
            nodeCount++;
        }
    });
    
    return demoNodes;
}

function generateRandomIP() {
    return `${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`;
}

function collectIPv4Hosts(nodesDict) {
    const hosts = [];
    for (const key in nodesDict) {
        const lastColon = key.lastIndexOf(":");
        if (lastColon === -1) continue;
        const host = key.substring(0, lastColon);
        if (isIPv4(host)) {
            hosts.push(host);
        }
    }
    return hosts;
}

async function geolocateIP(ip) {
    try {
        const url = GEOIP_URL.replace("{ip}", ip);
        const response = await fetch(url);
        const data = await response.json();
        if (data.status === "success" && data.lat && data.lon) {
            return [data.lat, data.lon];
        }
    } catch (error) {
    }
    return null;
}

async function geolocateHosts(hosts) {
    if (useDemoData && cachedLocations.length > 0) {
        return cachedLocations;
    }
    
    const locations = [];
    const batchSize = 5;
    const delay = 250;
    
    updateStatus(`Geolocating ${Math.min(hosts.length, MAX_IPS)} IPs...`, "info");
    
    for (let i = 0; i < Math.min(hosts.length, MAX_IPS); i += batchSize) {
        const batch = hosts.slice(i, i + batchSize);
        const promises = batch.map(ip => {
            if (ipToLocationCache[ip]) {
                return Promise.resolve(ipToLocationCache[ip]);
            }
            return geolocateIP(ip).then(loc => {
                if (loc) {
                    ipToLocationCache[ip] = loc;
                }
                return loc;
            });
        });
        const results = await Promise.all(promises);
        
        results.forEach(loc => {
            if (loc) locations.push(loc);
        });
        
        const progress = Math.min(100, ((i + batchSize) / Math.min(hosts.length, MAX_IPS)) * 100);
        updateStatus(`Geolocating... ${Math.round(progress)}%`, "info");
        
        if (i + batchSize < Math.min(hosts.length, MAX_IPS)) {
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
    
    return locations;
}

function updateMap(locations, totalNodes) {
    markersLayer.clearLayers();
    heatmapLayer.setLatLngs([]);
    
    if (locations.length > 0) {
        heatmapLayer.setLatLngs(locations);
        
        const markerLimit = 500;
        locations.slice(0, markerLimit).forEach(([lat, lon]) => {
            L.circleMarker([lat, lon], {
                radius: 3,
                fillColor: "#00d5ff",
                color: "#00d5ff",
                weight: 1,
                opacity: 0.7,
                fillOpacity: 0.7
            }).addTo(markersLayer);
        });
    }
    
    updateInfo(locations.length, totalNodes);
}

function updateStatus(message, type = "info") {
    const statusEl = document.getElementById("status");
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.className = `status ${type}`;
    }
    console.log(`[${type.toUpperCase()}] ${message}`);
}

function updateInfo(geolocatedCount, totalNodes) {
    const now = new Date().toLocaleString();
    
    const totalNodesEl = document.getElementById("total-nodes");
    const geolocatedNodesEl = document.getElementById("geolocated-nodes");
    const updateCountEl = document.getElementById("update-count");
    const lastUpdatedEl = document.getElementById("last-updated");
    
    if (totalNodesEl) {
        totalNodesEl.textContent = totalNodes.toLocaleString();
        totalNodesEl.classList.remove("loading");
    }
    if (geolocatedNodesEl) geolocatedNodesEl.textContent = geolocatedCount.toLocaleString();
    if (updateCountEl) updateCountEl.textContent = updateCount;
    if (lastUpdatedEl) lastUpdatedEl.textContent = now;
}

async function fetchAndUpdate() {
    if (isUpdating) return;
    
    isUpdating = true;
    updateCount++;
    
    try {
        updateStatus("Fetching live Bitcoin node data...", "info");
        
        const nodes = await fetchSnapshotNodes();
        
        if (!nodes) {
            if (cachedLocations.length > 0) {
                updateStatus("Using cached data.", "warning");
                updateMap(cachedLocations, cachedLocations.length * 30);
                updateInfo(cachedLocations.length, cachedLocations.length * 30);
            } else {
                updateStatus("Unable to fetch data. Will retry...", "error");
            }
            isUpdating = false;
            return;
        }
        
        const totalNodes = Object.keys(nodes).length;
        updateStatus(`Found ${totalNodes} nodes. Processing...`, "info");
        
        const hosts = collectIPv4Hosts(nodes);
        
        if (hosts.length === 0) {
            updateStatus("No IPv4 nodes found", "warning");
            updateMap([], 0);
            isUpdating = false;
            return;
        }
        
        const currentIPs = new Set(hosts);
        Object.keys(ipToLocationCache).forEach(ip => {
            if (!currentIPs.has(ip)) {
                delete ipToLocationCache[ip];
            }
        });
        
        let locations = [];
        
        if (useDemoData) {
            locations = cachedLocations;
        } else {
            const cachedLocationsList = [];
            const hostsNeedingGeolocation = [];
            
            hosts.forEach(ip => {
                if (ipToLocationCache[ip]) {
                    cachedLocationsList.push(ipToLocationCache[ip]);
                } else {
                    hostsNeedingGeolocation.push(ip);
                }
            });
            
            if (hostsNeedingGeolocation.length > 0) {
                updateStatus(`Geolocating ${hostsNeedingGeolocation.length} new IPs...`, "info");
                const newLocations = await geolocateHosts(hostsNeedingGeolocation);
                locations = [...cachedLocationsList, ...newLocations];
            } else {
                locations = cachedLocationsList;
                updateStatus(`Using cached locations (${locations.length} nodes)`, "info");
            }
        }
        
        if (locations.length > 0) {
            updateMap(locations, totalNodes);
            const dataType = useDemoData ? " (DEMO DATA)" : "";
            updateStatus(`✓ Update #${updateCount} - ${totalNodes.toLocaleString()} total nodes, ${locations.length.toLocaleString()} mapped${dataType}`, "success");
        } else {
            updateStatus("Waiting for geolocation data...", "warning");
        }
        
    } catch (error) {
        console.error("Error in fetchAndUpdate:", error);
        updateStatus("Error: " + error.message, "error");
    } finally {
        isUpdating = false;
    }
}

document.addEventListener('DOMContentLoaded', initMap);
