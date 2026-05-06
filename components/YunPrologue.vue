<template>
  <div class="yun-prologue-grid grid-bg">
    <YunAEFrame />
    <YunAERect />

    <div
      flex="~ col"
      class="yun-prologue-dock justify-center items-center absolute bottom-$rect-margin left-0 right-0 gap-2"
    >
      <div class="w-full px-2 flex justify-center">
        <InternetGacha />
      </div>
      <PrologueSocialLinks />
    </div>
  </div>
</template>

<style lang="scss">
/* 整块背景不拦截点击，避免挡住首页横幅里的友链/文章等按钮 */
.grid-bg.yun-prologue-grid {
  pointer-events: none;
}

.yun-prologue-dock {
  pointer-events: auto;
}

.grid-bg {
  --size: 40px;

  background:
    linear-gradient(90deg, rgb(255 255 255 / .1) 1px, transparent 1px),
    linear-gradient(rgb(255 255 255 / .1) 1px, transparent 1px);
  background-size: var(--size) var(--size);
}
</style>
