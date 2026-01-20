// 自定义主题 - 扩展 VitePress 默认主题
// https://vitepress.dev/guide/custom-theme
// https://vitepress.dev/guide/extending-default-theme

import { h, onMounted, watch, nextTick } from 'vue';
import type { Theme } from 'vitepress';
import DefaultTheme from 'vitepress/theme';
import { useRoute } from 'vitepress';

// 自定义样式
import './style.css';

// lite-tree 组件
import LiteTree from 'lite-tree';

export default {
  extends: DefaultTheme,

  Layout: () => {
    return h(DefaultTheme.Layout, null, {
      // 自定义插槽
      // https://vitepress.dev/guide/extending-default-theme#layout-slots
    });
  },

  enhanceApp({ app, router, siteData }) {
    // 注册全局组件
    app.component('LiteTree', LiteTree);

    // Live2D 看板娘 - 暂时禁用，模型 URL 不可用
    // 如需启用，请更换为可用的模型 URL
    // if (typeof window !== 'undefined') {
    //   import('oh-my-live2d').then(({ loadOml2d }) => {
    //     loadOml2d({
    //       models: [
    //         {
    //           // 使用你自己的模型 URL
    //           path: 'https://your-model-url/model.json',
    //           scale: 0.08,
    //           position: [0, 60],
    //           stageStyle: {
    //             height: 450
    //           }
    //         }
    //       ],
    //     });
    //   });
    // }
  },

  setup() {
    const route = useRoute();

    onMounted(() => {
      // 页面加载后的初始化逻辑
    });
  }
} satisfies Theme;
