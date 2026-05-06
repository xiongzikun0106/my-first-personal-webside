<script lang="ts" setup>
/**
 * 互联网非酋抽卡：R=.com/.net 随机域；
 * SR=The Useless Web 官网 uselessweb.js（与首页按钮同源）；
 * SSR=通过 B 站开放接口拉取收藏夹内视频，再随机一条（大保底）
 */
import { computed, onActivated, onMounted, ref } from 'vue'

/** 收藏夹页面 `fid` 与接口 `media_id` 相同 */
const BILI_FAV_MEDIA_ID = 3381047680

const BILI_FAVLIST_URL =
  'https://space.bilibili.com/514128180/favlist?fid=3381047680&ftype=create'

/** 收藏夹接口失败或解析为空时兜底 */
const SSR_POOL_FALLBACK_BILI: string[] = [
  BILI_FAVLIST_URL,
  'https://www.bilibili.com/video/BV1XWAuzBEwH/',
]

let ssrBvPromise: Promise<string[]> | null = null

/**
 * 分页拉取收藏夹内视频，组装标准播放页链接。
 * @see https://api.bilibili.com/x/v3/fav/resource/list
 */
async function fetchFavAllVideoUrls(): Promise<string[]> {
  const urls = new Set<string>()
  let pn = 1
  const ps = 40
  let hasMore = true

  while (hasMore && pn <= 60) {
    const qs = new URLSearchParams({
      media_id: String(BILI_FAV_MEDIA_ID),
      pn: String(pn),
      ps: String(ps),
      order: 'mtime',
      type: '0',
      platform: 'web',
    })
    const res = await fetch(
      `https://api.bilibili.com/x/v3/fav/resource/list?${qs.toString()}`,
      { credentials: 'omit', mode: 'cors' },
    )
    if (!res.ok)
      throw new Error(`bili fav ${res.status}`)

    const j = (await res.json()) as {
      code: number
      data?: {
        medias?: Array<{ bvid?: string; bv_id?: string }>
        has_more?: boolean
      }
    }
    if (j.code !== 0 || !j.data?.medias?.length)
      break

    for (const m of j.data.medias) {
      const bv = String(m.bvid || m.bv_id || '').trim()
      if (/^BV[a-zA-Z0-9]+$/.test(bv))
        urls.add(`https://www.bilibili.com/video/${bv}`)
    }

    hasMore = Boolean(j.data.has_more)
    pn += 1
  }

  return [...urls]
}

function getSSRPool(): Promise<string[]> {
  if (!ssrBvPromise) {
    ssrBvPromise = fetchFavAllVideoUrls()
      .then(list => (list.length ? list : SSR_POOL_FALLBACK_BILI))
      .catch(() => SSR_POOL_FALLBACK_BILI)
  }
  return ssrBvPromise
}

/** The Useless Web 脚本拉取失败时兜底 */
const SR_POOL_FALLBACK: string[] = [
  'https://heeeeeeeey.com/',
  'https://eelslap.com/',
  'https://www.staggeringbeauty.com/',
  'https://pointerpointer.com/',
  'https://corgiorgy.com/',
  'https://zoomquilt.org/',
  'https://thezen.zone/',
  'https://papertoilet.com/',
]

/**
 * 官网按钮同源数据：站点列表写在首页引用的脚本里。
 * @see https://theuselessweb.com/js/uselessweb.js
 */
const OFFICIAL_USELESS_WEB_JS =
  'https://theuselessweb.com/js/uselessweb.js'

function parseUselessWebJs(source: string): string[] {
  const urls = new Set<string>()
  for (const raw of source.split('\n')) {
    if (raw.trimStart().startsWith('//'))
      continue
    const line = raw.trimEnd()
    const re = /['"](https?:\/\/[^'"\\]+)['"]/g
    let m: RegExpExecArray | null
    while ((m = re.exec(line)) !== null) {
      try {
        urls.add(new URL(m[1]).href)
      }
      catch {
        /* ignore */
      }
    }
  }
  return [...urls]
}

let srSitesPromise: Promise<string[]> | null = null

async function fetchOfficialSRSites(): Promise<string[]> {
  const res = await fetch(OFFICIAL_USELESS_WEB_JS, {
    credentials: 'omit',
    mode: 'cors',
  })
  if (!res.ok)
    throw new Error(`TUW ${res.status}`)
  const urls = parseUselessWebJs(await res.text())
  if (!urls.length)
    throw new Error('TUW empty')
  return urls
}

function getSRPool(): Promise<string[]> {
  if (!srSitesPromise) {
    srSitesPromise = fetchOfficialSRSites()
      .then(list => (list.length ? list : SR_POOL_FALLBACK))
      .catch(() => SR_POOL_FALLBACK)
  }
  return srSitesPromise
}

const pityCount = ref(0)
const totalClicks = ref(0)
const successClicks = ref(0)
const lastProbeDetail = ref<string>('—')
/** 当前/上一轮祈愿探测的目标地址（出货与否都展示，便于未中时复制访问） */
const lastTargetUrl = ref('')

const pulling = ref(false)
const currentTier = ref<'R' | 'SR' | 'SSR' | null>(null)
const showPityTen = ref(false)
const showSSREffect = ref(false)
const announceText = ref('')

/** mulberry32 */
function mulberry32(seed: number) {
  return function () {
    let t = (seed += 0x6d2b79f5)
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const LEGACY_STORAGE_PREFIX = 'internet-gacha:'

/** 每次进入首页（含刷新；若外层包 KeepAlive 则再次进入也会触发）清零统计并重拉卡池缓存 */
function resetSession() {
  pityCount.value = 0
  totalClicks.value = 0
  successClicks.value = 0
  lastProbeDetail.value = '—'
  lastTargetUrl.value = ''
  announceText.value = ''
  showPityTen.value = false
  showSSREffect.value = false
  pulling.value = false
  currentTier.value = null

  ssrBvPromise = null
  srSitesPromise = null

  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const k = localStorage.key(i)
      if (k?.startsWith(LEGACY_STORAGE_PREFIX))
        localStorage.removeItem(k)
    }
  }
  catch {
    /* ignore */
  }
}

function warmupPools() {
  getSRPool().catch(() => {})
  getSSRPool().catch(() => {})
}

onMounted(() => {
  resetSession()
  warmupPools()
})

onActivated(() => {
  resetSession()
  warmupPools()
})

const rateText = computed(() => {
  const t = totalClicks.value
  if (t <= 0)
    return '—'
  return `${((successClicks.value / t) * 100).toFixed(1)}%`
})

function randomRLabel(rng: () => number) {
  const len = 4 + Math.floor(rng() * 5)
  let s = ''
  for (let i = 0; i < len; i++) {
    const k = Math.floor(rng() * 36)
    s += k < 10 ? String(k) : String.fromCharCode(97 + k - 10)
  }
  return s
}

function pickArr<T>(rng: () => number, arr: T[]): T {
  return arr[Math.floor(rng() * arr.length) % arr.length]
}

/**
 * 「出货」期望值：检定通过后再过此闸门，使总出货率约在 TARGET 附近。
 * 闸门 ≈ TARGET / ASSUMED_PROBE_OK（粗估单次网络检定通过率，可随观感微调）。
 */
const TARGET_OVERALL_SHIP_RATE = 0.1
const ASSUMED_PROBE_OK_RATE = 0.33
const POST_PROBE_OPEN_GATE = Math.min(1, TARGET_OVERALL_SHIP_RATE / ASSUMED_PROBE_OK_RATE)

/**
 * 探测「能否连上」：优先 favicon；再辅 no-cors fetch（完成即认为链路可用，非严格 HTTP 状态码）
 */
async function probeUrl(url: string): Promise<{ ok: boolean; detail: string }> {
  let origin: string
  try {
    origin = new URL(url).origin
  }
  catch {
    return { ok: false, detail: 'URL 无效' }
  }

  const faviconResult = await new Promise<{ ok: boolean; detail: string }>((resolve) => {
    const ms = 5500
    const tid = window.setTimeout(() => resolve({ ok: false, detail: 'Timeout' }), ms)
    const img = new Image()
    img.onload = () => {
      window.clearTimeout(tid)
      resolve({ ok: true, detail: '200 (favicon)' })
    }
    img.onerror = () => {
      window.clearTimeout(tid)
      resolve({ ok: false, detail: 'favicon Error' })
    }
    img.src = `${origin}/favicon.ico?_probe=${Date.now()}`
  })

  if (faviconResult.ok)
    return faviconResult

  try {
    await fetch(url, { mode: 'no-cors', cache: 'no-store' })
    return { ok: true, detail: '200 (opaque)' }
  }
  catch {
    return faviconResult.detail === 'Timeout'
      ? { ok: false, detail: 'Timeout' }
      : { ok: false, detail: `${faviconResult.detail} / fetch 失败` }
  }
}

function resetPityOnly() {
  pityCount.value = 0
}

function playSSR(url: string) {
  lastTargetUrl.value = url
  currentTier.value = 'SSR'
  lastProbeDetail.value = 'SSR 大保底'
  announceText.value =
    '超级无敌倒霉蛋就是你啦！砸到大保底了哦~ (╯°Д°)╯︵ ┻━┻'
  flashBurst('gold')
  showSSREffect.value = true
  pityCount.value = 0
  successClicks.value += 1

  window.setTimeout(() => {
    window.open(url, '_blank', 'noopener,noreferrer')
    showSSREffect.value = false
    announceText.value = ''
    currentTier.value = null
  }, 1800)
}

async function doPull() {
  if (pulling.value || showSSREffect.value)
    return

  const seed = (Date.now() ^ (Math.random() * 0xFFFFFFFF)) >>> 0
  const rng = mulberry32(seed || 1)

  totalClicks.value += 1

  if (pityCount.value >= 100) {
    const pool = await getSSRPool()
    const url = pickArr(rng, pool.length ? pool : SSR_POOL_FALLBACK_BILI)
    playSSR(url)
    return
  }

  /** R≈随机域名（旧版 Random Word API 同源玩法）；原为 80%，减半为 40% */
  const R_TIER_PROB = 0.4
  const tier: 'R' | 'SR' = rng() < R_TIER_PROB ? 'R' : 'SR'
  currentTier.value = tier

  let url: string
  if (tier === 'R') {
    const host = `${randomRLabel(rng)}.${rng() < 0.5 ? 'com' : 'net'}`
    url = `https://${host}/`
  }
  else {
    const srList = await getSRPool()
    url = pickArr(rng, srList.length ? srList : SR_POOL_FALLBACK)
  }

  lastTargetUrl.value = url

  pulling.value = true
  announceText.value = ''

  const probe = await probeUrl(url)
  pulling.value = false

  const gateOk = rng() < POST_PROBE_OPEN_GATE
  const shipped = probe.ok && gateOk
  lastProbeDetail.value = shipped
    ? probe.detail
    : probe.ok
      ? `${probe.detail}（未出货）`
      : probe.detail

  if (shipped) {
    successClicks.value += 1
    resetPityOnly()
    window.open(url, '_blank', 'noopener,noreferrer')

    if (tier === 'R')
      flashBurst('blue')
    else flashBurst('purple')
  }
  else {
    pityCount.value += 1
    if (pityCount.value >= 100) {
      const pool = await getSSRPool()
      const ssrUrl = pickArr(rng, pool.length ? pool : SSR_POOL_FALLBACK_BILI)
      playSSR(ssrUrl)
      return
    }
    if (pityCount.value === 10)
      showPityTen.value = true

    if (tier === 'R')
      flashBurst('blue')
    else flashBurst('purple')
  }

  currentTier.value = null
}


/** 简易闪光层 */
const flashRing = ref<'none' | 'blue' | 'purple' | 'gold'>('none')

function flashBurst(color: 'blue' | 'purple' | 'gold') {
  flashRing.value = color
  window.setTimeout(() => {
    flashRing.value = 'none'
  }, 900)
}
</script>

<template>
  <div class="igacha igacha--strip">
    <div
      class="igacha__flash"
      :class="{
        'igacha__flash--blue': flashRing === 'blue',
        'igacha__flash--purple': flashRing === 'purple',
        'igacha__flash--gold': flashRing === 'gold',
      }"
      aria-hidden="true"
    />

    <div class="igacha__strip-inner">
      <div class="igacha__row">
        <span
          class="igacha__brand"
          title="R 随机 .com/.net · SR The Useless Web 列表 · SSR B 站收藏夹随机；大保底水位 100"
        >随机互联网链接？但是抽卡</span>
        <div class="igacha__chips" aria-label="统计">
          <span class="igacha__chip">
            <span class="igacha__chip-k">出货率</span>{{ rateText }}
          </span>
          <span class="igacha__chip igacha__chip--dim">
            <span class="igacha__chip-k">大保底水位</span>{{ pityCount }}/100
          </span>
          <span
            class="igacha__chip igacha__chip--probe"
            :title="`本轮链接连通探测：${lastProbeDetail}`"
          >
            <span class="igacha__chip-k">探测</span>{{ lastProbeDetail }}
          </span>
          <span class="igacha__chip igacha__chip--dim">
            <span class="igacha__chip-k">总祈愿</span>{{ totalClicks }}<span class="igacha__chip-sep"> · </span><span class="igacha__chip-k">出货</span>{{ successClicks }}
          </span>
        </div>
        <button
          type="button"
          class="igacha__btn"
          :disabled="pulling || showSSREffect"
          @click="doPull"
        >
          <span v-if="pulling" class="igacha__btn-loading">…</span>
          <span v-else>祈愿</span>
        </button>
      </div>
      <div class="igacha__url-line">
        <span class="igacha__url-label">URL</span>
        <template v-if="lastTargetUrl">
          <a
            class="igacha__url"
            :href="lastTargetUrl"
            target="_blank"
            rel="noopener noreferrer"
            :title="lastTargetUrl"
          >{{ lastTargetUrl }}</a>
        </template>
        <span v-else class="igacha__url igacha__url--muted">祈愿后显示</span>
      </div>
    </div>

    <!-- 10 连非酋提示 -->
    <Teleport to="body">
      <div v-if="showPityTen" class="igacha__modal-mask" @click.self="showPityTen = false">
        <div class="igacha__modal" role="dialog" aria-modal="true">
          <p class="igacha__modal-text">
            杂鱼非酋倒霉蛋~还要继续吗？(˵¯͒〰¯͒˵)
          </p>
          <button type="button" class="igacha__modal-btn" @click="showPityTen = false">
            继续抽
          </button>
        </div>
      </div>
    </Teleport>

    <!-- SSR 大保底全屏金光 -->
    <Teleport to="body">
      <div v-if="showSSREffect" class="igacha__ssr">
        <div class="igacha__ssr-rays" />
        <p class="igacha__ssr-text">
          {{ announceText }}
        </p>
      </div>
    </Teleport>
  </div>
</template>

<style scoped lang="scss">
.igacha {
  position: relative;
  z-index: 3;
}

.igacha--strip {
  width: 100%;
  max-width: min(92vw, 34rem);
}

.igacha__strip-inner {
  padding: 0.32rem 0.5rem 0.36rem;
  border-radius: 10px;
  background: color-mix(in srgb, var(--va-c-bg) 58%, transparent);
  border: 1px solid color-mix(in srgb, var(--va-c-text) 12%, transparent);
  box-shadow:
    0 0 0 1px rgb(255 255 255 / 0.03) inset,
    0 3px 12px rgb(0 0 0 / 0.12);
  backdrop-filter: blur(6px);
}

.igacha__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.45rem;
}

.igacha__brand {
  flex-shrink: 0;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--va-c-text);
  text-shadow: 0 0 10px color-mix(in srgb, var(--va-c-primary) 35%, transparent);
}

.igacha__chips {
  display: flex;
  flex: 1 1 8rem;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.2rem 0.35rem;
  min-width: 0;
  font-size: 0.56rem;
  line-height: 1.25;
  color: var(--va-c-text-2, var(--va-c-text));
}

.igacha__chip {
  padding: 0.12rem 0.32rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--va-c-text) 6%, transparent);
  white-space: nowrap;
}

.igacha__chip-k {
  margin-inline-end: 0.28em;
  opacity: 0.72;
  font-weight: 600;
}

.igacha__chip-sep {
  opacity: 0.42;
}

.igacha__chip--dim {
  opacity: 0.78;
}

.igacha__chip--probe {
  max-width: min(40vw, 9rem);
  overflow: hidden;
  text-overflow: ellipsis;
}

.igacha__url-line {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-top: 0.28rem;
  padding-top: 0.26rem;
  border-top: 1px solid color-mix(in srgb, var(--va-c-divider) 70%, transparent);
  min-width: 0;
}

.igacha__url-label {
  flex-shrink: 0;
  font-size: 0.52rem;
  opacity: 0.75;
  letter-spacing: 0.02em;
  color: var(--va-c-text-2, var(--va-c-text));
}

.igacha__url {
  flex: 1 1 0;
  min-width: 0;
  display: block;
  font-family: var(--va-font-mono, ui-monospace, monospace);
  font-size: 0.52rem;
  line-height: 1.4;
  color: var(--va-c-primary);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;

  &:hover {
    text-decoration: underline;
  }
}

.igacha__url--muted {
  color: var(--va-c-text-2, var(--va-c-text));
  opacity: 0.65;
  font-family: inherit;
}

.igacha__btn {
  flex-shrink: 0;
  margin-left: auto;
  padding: 0.26rem 0.75rem;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  font-size: 0.62rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--va-c-bg);
  background: linear-gradient(
    165deg,
    var(--va-c-primary) 0%,
    color-mix(in srgb, var(--va-c-primary) 70%, #3050c8) 100%
  );
  box-shadow: 0 2px 12px color-mix(in srgb, var(--va-c-primary) 32%, transparent);
  transition:
    transform 0.15s ease,
    filter 0.15s ease;

  &:hover:not(:disabled) {
    transform: translateY(-1px);
    filter: brightness(1.06);
  }

  &:disabled {
    opacity: 0.65;
    cursor: not-allowed;
  }
}

.igacha__btn-loading {
  display: inline-block;
  animation: igacha-pulse 0.85s ease-in-out infinite;
}

@keyframes igacha-pulse {
  50% {
    opacity: 0.55;
  }
}

.igacha__flash {
  pointer-events: none;
  position: absolute;
  inset: -6px;
  border-radius: 14px;
  opacity: 0;
  z-index: -1;
  transition: opacity 0.15s ease;

  &--blue {
    opacity: 1;
    animation: igacha-flash-blue 0.85s ease-out;
  }

  &--purple {
    opacity: 1;
    animation: igacha-flash-purple 0.85s ease-out;
  }

  &--gold {
    opacity: 1;
    animation: igacha-flash-gold 1.1s ease-out;
  }
}

@keyframes igacha-flash-blue {
  0% {
    box-shadow:
      0 0 0 0 rgb(80 160 255 / 0.9),
      0 0 40px rgb(80 180 255 / 0.45);
  }

  100% {
    box-shadow:
      0 0 0 12px transparent,
      0 0 0 transparent;
  }
}

@keyframes igacha-flash-purple {
  0% {
    box-shadow:
      0 0 0 0 rgb(180 120 255 / 0.95),
      0 0 48px rgb(200 100 255 / 0.5);
  }

  100% {
    box-shadow:
      0 0 0 14px transparent,
      0 0 0 transparent;
  }
}

@keyframes igacha-flash-gold {
  0% {
    box-shadow:
      0 0 0 0 rgb(255 215 120 / 1),
      0 0 56px rgb(255 200 80 / 0.55);
  }

  100% {
    box-shadow:
      0 0 0 18px transparent,
      0 0 0 transparent;
  }
}

.igacha__modal-mask {
  position: fixed;
  inset: 0;
  z-index: 99998;
  background: rgb(0 0 0 / 0.42);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(3px);
}

.igacha__modal {
  width: min(92vw, 320px);
  padding: 1rem 1rem 0.85rem;
  border-radius: 12px;
  background: var(--va-c-bg);
  border: 1px solid var(--va-c-divider);
  box-shadow: 0 18px 48px rgb(0 0 0 / 0.35);
}

.igacha__modal-text {
  margin: 0 0 0.75rem;
  font-size: 0.82rem;
  line-height: 1.5;
  color: var(--va-c-text);
}

.igacha__modal-btn {
  width: 100%;
  padding: 0.4rem;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-weight: 600;
  color: var(--va-c-bg);
  background: var(--va-c-primary);
}

.igacha__ssr {
  position: fixed;
  inset: 0;
  z-index: 99999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(
    circle at 50% 40%,
    rgb(255 240 180 / 0.35) 0%,
    rgb(20 12 4 / 0.88) 55%,
    rgb(0 0 0 / 0.92) 100%
  );
  animation: igacha-ssr-bg 1.8s ease-out forwards;
  pointer-events: none;
}

@keyframes igacha-ssr-bg {
  0% {
    opacity: 0;
  }

  12% {
    opacity: 1;
  }

  100% {
    opacity: 1;
  }
}

.igacha__ssr-rays {
  position: absolute;
  inset: -20%;
  background: repeating-conic-gradient(
    from 0deg at 50% 50%,
    rgb(255 220 140 / 0.16) 0deg 6deg,
    transparent 6deg 14deg
  );
  animation: igacha-spin 8s linear infinite;
  opacity: 0.75;
}

@keyframes igacha-spin {
  to {
    transform: rotate(360deg);
  }
}

.igacha__ssr-text {
  position: relative;
  z-index: 2;
  margin: 0;
  max-width: min(90vw, 26rem);
  text-align: center;
  font-size: clamp(0.9rem, 3.2vw, 1.1rem);
  font-weight: 800;
  line-height: 1.45;
  color: #fff8e8;
  text-shadow:
    0 0 20px rgb(255 200 80 / 1),
    0 0 40px rgb(255 160 40 / 0.8);
}
</style>
