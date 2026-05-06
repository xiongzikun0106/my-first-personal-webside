<script lang="ts" setup>
import { onMounted, ref } from 'vue'
import tlds from 'tlds'

const RANDOM_WORD_API =
  'https://random-word-api.herokuapp.com/word?number=1&lang=en'

/** mulberry32: deterministic PRNG from 32-bit seed */
function mulberry32(seed: number) {
  return function () {
    let t = (seed += 0x6d2b79f5)
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** Root-zone style labels only: single segment, ASCII letters a–z (excludes xn-- / IDN). */
function buildLatinSingleLabelTldPool(raw: readonly string[]): string[] {
  const set = new Set<string>()
  for (const entry of raw) {
    const t = entry.toLowerCase()
    if (t.includes('.'))
      continue
    if (!/^[a-z]+$/.test(t))
      continue
    set.add(t)
  }
  return [...set]
}

const hostname = ref('…')
const href = ref('https://example.com/')
const resolved = ref(false)

const TITLE_HINT =
  '使用随机英文单词和随机后缀组成的随机网站，虽然大概率是404 (´・ω・`)'

async function fetchEnglishWordOnce(): Promise<string> {
  const res = await fetch(RANDOM_WORD_API)
  if (!res.ok)
    throw new Error(`Random Word API: ${res.status}`)
  const data = await res.json() as unknown
  if (!Array.isArray(data) || data.length === 0)
    throw new Error('Random Word API: empty')
  const raw = data[0]
  if (typeof raw !== 'string' || !raw.trim())
    throw new Error('Random Word API: invalid word')
  const cleaned = raw.toLowerCase().trim().replace(/[^a-z0-9-]/g, '')
    .replace(/^-+|-+$/g, '')
  if (!cleaned)
    throw new Error('Random Word API: no usable label')
  return cleaned
}

async function fetchEnglishWord(): Promise<string> {
  try {
    return await fetchEnglishWordOnce()
  }
  catch {
    await new Promise(r => setTimeout(r, 400))
    try {
      return await fetchEnglishWordOnce()
    }
    catch {
      return 'hello'
    }
  }
}

onMounted(async () => {
  const seed = Date.now() % 0xffffffff
  const rng = mulberry32(seed === 0 ? 1 : seed)

  const latinTlds = buildLatinSingleLabelTldPool(tlds as string[])
  const tldPool = latinTlds.length > 0 ? latinTlds : ['com', 'net', 'org']

  const word = await fetchEnglishWord()
  const tld = tldPool[Math.floor(rng() * tldPool.length)] || 'com'

  const host = `${word}.${tld}`
  hostname.value = host
  href.value = `https://${host}/`
  resolved.value = true
})
</script>

<template>
  <div class="random-site-link-wrap">
    <a
      class="random-site-link"
      :href="href"
      target="_blank"
      rel="noopener noreferrer"
      :title="TITLE_HINT"
    >
      <span class="random-site-link__label">随机网站：</span>
      <span
        class="random-site-link__host"
        :class="{ 'random-site-link__host--pending': !resolved }"
      >{{ hostname }}</span>
    </a>
  </div>
</template>

<style lang="scss" scoped>
.random-site-link-wrap {
  display: flex;
  justify-content: center;
  z-index: 2;
}

.random-site-link {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: center;
  gap: 0.15em;
  max-width: min(90vw, 28rem);
  padding: 0.2rem 0.35rem;
  background: transparent;
  color: var(--va-c-text);
  text-decoration: none;
  border-radius: 4px;
  font-size: 0.8rem;
  line-height: 1.4;
  transition:
    color var(--va-transition-duration, 0.2s),
    opacity var(--va-transition-duration, 0.2s);

  &:hover,
  &:focus-visible {
    color: var(--va-c-primary);
    outline: none;
  }
}

.random-site-link__label {
  flex-shrink: 0;
  opacity: 0.9;
}

.random-site-link__host {
  font-family: var(--va-font-mono, ui-monospace, monospace);
  word-break: break-all;
  text-align: center;
}

.random-site-link__host--pending {
  opacity: 0.65;
}
</style>
