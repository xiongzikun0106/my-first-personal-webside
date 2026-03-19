<script lang="ts" setup>
import { useFrontmatter, usePostTitle } from 'valaxy'
import { computed } from 'vue'

const frontmatter = useFrontmatter()
const title = usePostTitle(frontmatter)
const links = computed(() => frontmatter.value.links || [])
</script>

<template>
  <YunLayoutWrapper>
    <YunLayoutLeft />

    <RouterView v-slot="{ Component }">
      <component :is="Component">
        <template #main-header>
          <YunPageHeader
            :title="title || '友情链接'"
            :icon="frontmatter.icon || 'i-ri-links-line'"
            :color="frontmatter.color"
          />
        </template>
        <template #main-content>
          <YunLinks :links="links" :random="frontmatter.random || false" />
          <slot />
        </template>
      </component>
    </RouterView>
  </YunLayoutWrapper>

  <YunFooter />
</template>
