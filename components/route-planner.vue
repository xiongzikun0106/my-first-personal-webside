<script lang="ts" setup>
/**
 * route-planner.vue — 纯前端「选区域 → 绘制 → 拟合到道路 → 导出」工具。
 *
 * 设计要点：
 *  - 完全浏览器端运行，零后端、零日常服务依赖（OSM 底图 + Overpass 路网）。
 *  - 通过 CDN 在客户端注入 Leaflet + Leaflet-Geoman，避免 SSR 报错，也不新增 npm 依赖。
 *  - 拟合到道路：用 Overpass API 拉取绘制区域内的 OSM 道路，把每个顶点吸附到最近路段。
 *  - 导出：GPX / TCX / GeoJSON 前端直接生成下载。
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

// CDN 依赖（jsdelivr，已确认可访问）
const LEAFLET_CSS = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css'
const LEAFLET_JS = 'https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js'
const GEOMAN_CSS = 'https://cdn.jsdelivr.net/npm/@geoman-io/leaflet-geoman-free@2.17.0/dist/leaflet-geoman.css'
const GEOMAN_JS = 'https://cdn.jsdelivr.net/npm/@geoman-io/leaflet-geoman-free@2.17.0/dist/leaflet-geoman.min.js'

// Overpass 公共实例（含中文站注释，个人站流量足够）
const OVERPASS_ENDPOINTS = [
  'https://overpass-api.de/api/interpreter',
  'https://overpass.kumi.systems/api/interpreter',
]

const mapEl = ref<HTMLDivElement | null>(null)
const ready = ref(false)
const busy = ref(false)
const status = ref('正在加载地图…')
const distText = ref('0 m')
const ptText = ref('0 点')
const hasData = ref(false)

// 运行时对象（非响应式）
let map: any = null
let L: any = null
let layers: any[] = []

function loadCss(href: string) {
  return new Promise<void>((resolve, reject) => {
    const el = document.createElement('link')
    el.rel = 'stylesheet'
    el.href = href
    el.onload = () => resolve()
    el.onerror = () => reject(new Error('样式加载失败'))
    document.head.appendChild(el)
  })
}

function loadScript(src: string) {
  return new Promise<void>((resolve, reject) => {
    const el = document.createElement('script')
    el.src = src
    el.onload = () => resolve()
    el.onerror = () => reject(new Error('脚本加载失败'))
    document.head.appendChild(el)
  })
}

async function loadLibs() {
  await loadCss(LEAFLET_CSS)
  await loadScript(LEAFLET_JS)
  if (typeof (window as any).L === 'undefined')
    throw new Error('Leaflet 未就绪')
  await loadCss(GEOMAN_CSS)
  await loadScript(GEOMAN_JS)
  L = (window as any).L
  if (typeof L.PM === 'undefined')
    throw new Error('Leaflet-Geoman 未就绪')
}

// —— 地图初始化 ——
function initMap() {
  // 默认视野：成都（可自行拖动，仅做起点）
  map = L.map(mapEl.value, { zoomControl: true }).setView([30.57, 104.06], 13)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map)

  // Geoman 工具栏：保留编辑/删除，绘制交给下方自定义按钮
  map.pm.addControls({
    position: 'topleft',
    drawMarker: false,
    drawPolyline: false,
    drawPolygon: false,
    drawRectangle: false,
    drawCircle: false,
    drawCircleMarker: false,
    cutPolygon: false,
    editMode: true,
    dragMode: true,
    removalMode: true,
    rotateMode: false,
    snapping: true,
    pinning: false,
  })

  map.on('pm:create', (e: any) => {
    const layer = e.layer
    layers.push(layer)
    layer.on('pm:edit', refreshStats)
    layer.on('pm:update', refreshStats)
    layer.on('pm:remove', () => {
      layers = layers.filter(l => l !== layer)
      refreshStats()
    })
    layer.on('pm:dragend', refreshStats)
    refreshStats()
    status.value = '已绘制。双击可继续加顶点，左侧可编辑/删除；画好后点「拟合到道路」。'
  })
}

// —— 工具方法 ——
function lineLayers() {
  return layers.filter((l: any) => l instanceof L.Polyline && !(l instanceof L.Polygon))
}

function collectRoutePoints(): { lat: number; lng: number }[] {
  const pts: { lat: number; lng: number }[] = []
  for (const line of lineLayers()) {
    const latlngs = line.getLatLngs()
    for (const ll of latlngs) {
      if (ll && (ll as any).lat != null) pts.push({ lat: ll.lat, lng: ll.lng })
    }
  }
  return pts
}

function refreshStats() {
  const latlngs = lineLayers().flatMap((l: any) => l.getLatLngs())
  let d = 0
  for (let i = 0; i < latlngs.length - 1; i++) {
    if (map && latlngs[i] && latlngs[i + 1]) d += map.distance(latlngs[i], latlngs[i + 1])
  }
  distText.value = d >= 1000 ? `${(d / 1000).toFixed(2)} km` : `${Math.round(d)} m`
  ptText.value = `${latlngs.length} 点`
  hasData.value = lineLayers().length > 0
}

// —— 绘制 ——
function drawLine() {
  map.pm.enableDraw('Line', {})
  status.value = '绘制路线：单击加顶点，双击结束。'
}

function drawFreehand() {
  map.pm.enableDraw('Line', { freehand: true })
  status.value = '自由手绘路线：按住拖动即可，松开结束。'
}

function drawPolygon() {
  map.pm.enableDraw('Polygon', {})
  status.value = '绘制区域：单击加顶点，双击闭合。'
}

function drawRectangle() {
  map.pm.enableDraw('Rectangle', {})
  status.value = '拖拽框选一个矩形区域。'
}

function cancelDraw() {
  map.pm.disableDraw()
  status.value = '已取消绘制。'
}

function clearAll() {
  map.pm.disableDraw()
  for (const l of [...layers]) map.removeLayer(l)
  layers = []
  hasData.value = false
  distText.value = '0 m'
  ptText.value = '0 点'
  status.value = '已清空。'
}

// —— 拟合到道路（Overpass + 最近路段吸附） ——
// 用 Overpass POST，URL 编码查询
async function overpassQuery(query: string): Promise<{ geometry: [number, number][][] }[]> {
  let lastErr: Error | null = null
  for (const ep of OVERPASS_ENDPOINTS) {
    try {
      const res = await fetch(ep, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `data=${encodeURIComponent(query)}`,
      })
      if (!res.ok)
        throw new Error(`Overpass ${res.status}`)
      const data = await res.json()
      const ways: { geometry: [number, number][][] }[] = []
      for (const el of data.elements || []) {
        if (el.type === 'way' && Array.isArray(el.geometry)) {
          const seg: [number, number][] = el.geometry.map((g: any) => [g.lat, g.lon])
          if (seg.length > 1) ways.push({ geometry: seg })
        }
      }
      return ways
    }
    catch (e: any) {
      lastErr = e
    }
  }
  throw lastErr || new Error('Overpass 请求失败')
}

function snapVertexToWays(px: number, py: number, waysMeters: [number, number][][]) {
  let best: { x: number; y: number } | null = null
  let bestD = Infinity
  for (const seg of waysMeters) {
    for (let i = 0; i < seg.length - 1; i++) {
      const ax = seg[i][0]
      const ay = seg[i][1]
      const bx = seg[i + 1][0]
      const by = seg[i + 1][1]
      const dx = bx - ax
      const dy = by - ay
      const len2 = dx * dx + dy * dy
      let t = len2 === 0 ? 0 : ((px - ax) * dx + (py - ay) * dy) / len2
      t = Math.max(0, Math.min(1, t))
      const x = ax + t * dx
      const y = ay + t * dy
      const d = (px - x) * (px - x) + (py - y) * (py - y)
      if (d < bestD) {
        bestD = d
        best = { x, y }
      }
    }
  }
  return best
}

async function fitToRoads() {
  const target = lineLayers()
  if (target.length === 0) {
    status.value = '请先绘制一条路线（自由手绘或折线）。'
    return
  }
  busy.value = true
  status.value = '正在拟合道路…'
  try {
    // 统计所有路线的外包框
    const bounds = L.latLngBounds([])
    for (const line of target) bounds.extend(line.getBounds())
    const s = bounds.getSouth()
    const w = bounds.getWest()
    const n = bounds.getNorth()
    const e = bounds.getEast()
    if (n - s < 1e-6 || e - w < 1e-6) {
      status.value = '路线范围太小，无法获取道路。'
      return
    }

    // Overpass：拉取该范围内常见道路
    const roadFilter = 'way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|service|living_street|pedestrian|track|path)$"]'
    const bb = `(${s},${w},${n},${e})`
    const query = `[out:json][timeout:25];(${roadFilter}${bb};);out geom;`
    const ways = await overpassQuery(query)

    if (ways.length === 0) {
      status.value = '该范围内没有匹配的道路。'
      return
    }

    const refLat = (s + n) / 2
    const R = 6378137
    const cosLat = Math.cos(refLat * Math.PI / 180)
    const toXY = (lat: number, lng: number) => [R * lng * Math.PI / 180 * cosLat, R * lat * Math.PI / 180] as [number, number]
    const fromXY = (x: number, y: number) => {
      const lng = x / (R * cosLat) * 180 / Math.PI
      const lat = y / R * 180 / Math.PI
      return { lat, lng }
    }

    // 预先把道路端点投到平面米制坐标
    const waysMeters: [number, number][][] = ways.map(w => w.geometry.map(g => toXY(g[0], g[1])))

    for (const line of target) {
      const latlngs: any[] = line.getLatLngs()
      const snapped = latlngs.map((ll: any) => {
        const [x, y] = toXY(ll.lat, ll.lng)
        const best = snapVertexToWays(x, y, waysMeters)
        if (!best)
          return ll
        const { lat, lng } = fromXY(best.x, best.y)
        return L.latLng(lat, lng)
      })
      line.setLatLngs(snapped)
    }

    refreshStats()
    status.value = `已拟合到 ${ways.length} 条道路，可导出 GPX / TCX / GeoJSON。`
  }
  catch (e: any) {
    status.value = `拟合失败：${e?.message || e}`
  }
  finally {
    busy.value = false
  }
}

// —— 导出 ——
function download(name: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function requireRoute(): { lat: number; lng: number }[] | null {
  const pts = collectRoutePoints()
  if (pts.length < 2) {
    status.value = '没有可导出的路线，请先绘制一条路线。'
    return null
  }
  return pts
}

function exportGpx() {
  const pts = requireRoute()
  if (!pts)
    return
  const trkpts = pts.map(p => `      <trkpt lat="${p.lat}" lon="${p.lng}"></trkpt>`).join('\n')
  const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="mikotossd-route-planner" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Route</name>
    <trkseg>
${trkpts}
    </trkseg>
  </trk>
</gpx>`
  download('route.gpx', gpx, 'application/gpx+xml')
  status.value = '已导出 GPX。'
}

function exportTcx() {
  const pts = requireRoute()
  if (!pts)
    return
  const now = new Date().toISOString()
  const tps = pts.map(p => `        <Trackpoint>
          <Position>
            <LatitudeDegrees>${p.lat}</LatitudeDegrees>
            <LongitudeDegrees>${p.lng}</LongitudeDegrees>
          </Position>
          <Time>${now}</Time>
        </Trackpoint>`).join('\n')
  const tcx = `<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd">
  <Courses>
    <Course>
      <Name>Route</Name>
      <Track>
${tps}
      </Track>
    </Course>
  </Courses>
</TrainingCenterDatabase>`
  download('route.tcx', tcx, 'application/vnd.garmin.tcx+xml')
  status.value = '已导出 TCX。'
}

function exportGeoJson() {
  const pts = requireRoute()
  if (!pts)
    return
  const fc = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: {},
        geometry: { type: 'LineString', coordinates: pts.map(p => [p.lng, p.lat]) },
      },
    ],
  }
  download('route.geojson', JSON.stringify(fc, null, 2), 'application/geo+json')
  status.value = '已导出 GeoJSON。'
}

// —— 生命周期 ——
let loaded = false

onMounted(async () => {
  if (typeof window === 'undefined')
    return
  try {
    if (!loaded) {
      await loadLibs()
      loaded = true
    }
    initMap()
    ready.value = true
    status.value = '地图已就绪。用下方按钮选区域、画路线，画完点「拟合到道路」。'
  }
  catch (e: any) {
    status.value = `加载地图失败：${e?.message || e}`
  }
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <div class="route-planner">
    <div v-if="!ready" class="rp-loading">{{ status }}</div>

    <template v-else>
      <div class="rp-toolbar">
        <button class="rp-btn" @click="drawFreehand">✏️ 自由手绘</button>
        <button class="rp-btn" @click="drawLine">📏 折线</button>
        <button class="rp-btn" @click="drawPolygon">⬠ 区域多边形</button>
        <button class="rp-btn" @click="drawRectangle">▭ 矩形区域</button>
        <button class="rp-btn" @click="cancelDraw">✖ 取消</button>
        <button class="rp-btn rp-btn--primary" :disabled="busy" @click="fitToRoads">🧭 拟合到道路</button>
        <button class="rp-btn" :disabled="!hasData" @click="exportGpx">下载 GPX</button>
        <button class="rp-btn" :disabled="!hasData" @click="exportTcx">下载 TCX</button>
        <button class="rp-btn" :disabled="!hasData" @click="exportGeoJson">下载 GeoJSON</button>
        <button class="rp-btn rp-btn--danger" @click="clearAll">🗑 清空</button>
      </div>

      <div class="rp-stats">
        <span class="rp-stat">📏 {{ distText }}</span>
        <span class="rp-stat">📍 {{ ptText }}</span>
        <span class="rp-status">{{ status }}</span>
      </div>
    </template>

    <!-- 地图容器始终渲染,确保 onMounted 时容器已在 DOM,避免 Map container not found -->
    <div ref="mapEl" class="rp-mapbox" />
  </div>
</template>

<style scoped>
.route-planner {
  width: 100%;
  margin-top: 0.5rem;
}
.rp-loading {
  padding: 2rem;
  text-align: center;
  color: var(--va-c-text-2);
}
.rp-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 0.5rem;
}
.rp-btn {
  padding: 0.35rem 0.6rem;
  border: 1px solid var(--va-c-divider, #ddd);
  border-radius: 6px;
  background: var(--va-c-bg, #fff);
  color: var(--va-c-text);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.15s;
}
.rp-btn:hover:not(:disabled) {
  border-color: var(--va-c-primary);
  color: var(--va-c-primary);
}
.rp-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.rp-btn--primary {
  background: var(--va-c-primary);
  color: #fff;
  border-color: var(--va-c-primary);
}
.rp-btn--primary:hover:not(:disabled) {
  filter: brightness(1.08);
  color: #fff;
}
.rp-btn--danger {
  color: #e74c3c;
  border-color: #e74c3c;
}
.rp-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
}
.rp-stat {
  font-weight: 600;
  white-space: nowrap;
}
.rp-status {
  color: var(--va-c-text-2);
  flex: 1 1 auto;
  min-width: 200px;
}
.rp-mapbox {
  width: 100%;
  height: 65vh;
  min-height: 420px;
  border: 1px solid var(--va-c-divider, #ddd);
  border-radius: 8px;
  overflow: hidden;
  z-index: 1;
}
</style>
