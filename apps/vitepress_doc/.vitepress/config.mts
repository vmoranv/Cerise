import { defineConfig } from 'vitepress';

export default defineConfig({
  title: "Cerise",
  description: "AI-powered Live2D Virtual Character Core System",

  // i18n 配置
  locales: {
    root: {
      label: '简体中文',
      lang: 'zh-CN',
      title: 'Cerise',
      description: 'AI 驱动的 Live2D 虚拟角色核心系统',
      themeConfig: {
        nav: [
          { text: '首页', link: '/' },
          { text: '指南', link: '/guide/' },
          { text: 'API', link: '/api/' },
          { text: '插件', link: '/plugins/' },
          { text: '开发', link: '/development/' }
        ],
        sidebar: {
          '/guide/': [
            {
              text: '入门',
              items: [
                { text: '简介', link: '/guide/' },
                { text: '快速开始', link: '/guide/getting-started' },
                { text: '配置', link: '/guide/configuration' }
              ]
            },
            {
              text: '核心概念',
              items: [
                { text: '架构概览', link: '/guide/architecture' },
                { text: 'AI Provider', link: '/guide/ai-providers' },
                { text: '角色系统', link: '/guide/character' },
                { text: '情感引擎', link: '/guide/emotion' },
                { text: '记忆系统', link: '/guide/memory' }
              ]
            },
            {
              text: '进阶',
              items: [
                { text: '插件开发', link: '/guide/plugin-development' },
                { text: 'Live2D 集成', link: '/guide/live2d' },
                { text: 'TTS 集成', link: '/guide/tts' }
              ]
            }
          ],
          '/api/': [
            {
              text: 'API 参考',
              items: [
                { text: '概览', link: '/api/' },
                { text: 'REST API', link: '/api/rest' },
                { text: 'WebSocket', link: '/api/websocket' }
              ]
            }
          ],
          '/plugins/': [
            {
              text: '插件',
              items: [
                { text: '插件列表', link: '/plugins/' },
                { text: '开发指南', link: '/plugins/development' }
              ]
            }
          ],
          '/development/': [
            {
              text: '开发',
              items: [
                { text: '概览', link: '/development/' },
                { text: '记忆层迁移日志', link: '/development/memory-layer-integration-log' }
              ]
            }
          ]
        },
        docFooter: {
          prev: '上一页',
          next: '下一页'
        },
        outline: {
          label: '页面导航'
        },
        lastUpdated: {
          text: '最后更新于'
        },
        returnToTopLabel: '回到顶部',
        sidebarMenuLabel: '菜单',
        darkModeSwitchLabel: '主题',
        lightModeSwitchTitle: '切换到浅色模式',
        darkModeSwitchTitle: '切换到深色模式'
      }
    },
    en: {
      label: 'English',
      lang: 'en-US',
      link: '/en/',
      title: 'Cerise',
      description: 'AI-powered Live2D Virtual Character Core System',
      themeConfig: {
        nav: [
          { text: 'Home', link: '/en/' },
          { text: 'Guide', link: '/en/guide/' },
          { text: 'API', link: '/en/api/' },
          { text: 'Plugins', link: '/en/plugins/' }
        ],
        sidebar: {
          '/en/guide/': [
            {
              text: 'Getting Started',
              items: [
                { text: 'Introduction', link: '/en/guide/' },
                { text: 'Quick Start', link: '/en/guide/getting-started' },
                { text: 'Configuration', link: '/en/guide/configuration' }
              ]
            },
            {
              text: 'Core Concepts',
              items: [
                { text: 'Architecture', link: '/en/guide/architecture' },
                { text: 'AI Providers', link: '/en/guide/ai-providers' },
                { text: 'Character System', link: '/en/guide/character' },
                { text: 'Emotion Engine', link: '/en/guide/emotion' },
                { text: 'Memory System', link: '/en/guide/memory' }
              ]
            },
            {
              text: 'Advanced',
              items: [
                { text: 'Plugin Development', link: '/en/guide/plugin-development' },
                { text: 'Live2D Integration', link: '/en/guide/live2d' },
                { text: 'TTS Integration', link: '/en/guide/tts' }
              ]
            }
          ],
          '/en/api/': [
            {
              text: 'API Reference',
              items: [
                { text: 'Overview', link: '/en/api/' },
                { text: 'REST API', link: '/en/api/rest' },
                { text: 'WebSocket', link: '/en/api/websocket' }
              ]
            }
          ],
          '/en/plugins/': [
            {
              text: 'Plugins',
              items: [
                { text: 'Plugin List', link: '/en/plugins/' },
                { text: 'Development Guide', link: '/en/plugins/development' }
              ]
            }
          ]
        },
        docFooter: {
          prev: 'Previous',
          next: 'Next'
        },
        outline: {
          label: 'On this page'
        },
        lastUpdated: {
          text: 'Last updated'
        },
        returnToTopLabel: 'Back to top',
        sidebarMenuLabel: 'Menu',
        darkModeSwitchLabel: 'Theme',
        lightModeSwitchTitle: 'Switch to light theme',
        darkModeSwitchTitle: 'Switch to dark theme'
      }
    }
  },

  themeConfig: {
    socialLinks: [
      { icon: 'github', link: 'https://github.com/your-username/cerise' }
    ],
    search: {
      provider: 'local',
      options: {
        locales: {
          root: {
            translations: {
              button: {
                buttonText: '搜索文档',
                buttonAriaLabel: '搜索文档'
              },
              modal: {
                noResultsText: '无法找到相关结果',
                resetButtonTitle: '清除查询条件',
                footer: {
                  selectText: '选择',
                  navigateText: '切换'
                }
              }
            }
          },
          en: {
            translations: {
              button: {
                buttonText: 'Search',
                buttonAriaLabel: 'Search'
              },
              modal: {
                noResultsText: 'No results found',
                resetButtonTitle: 'Clear query',
                footer: {
                  selectText: 'Select',
                  navigateText: 'Navigate'
                }
              }
            }
          }
        }
      }
    }
  },

  // Markdown 配置 - 使用内置代码块语法高亮
  markdown: {
    lineNumbers: true,
    // 如需 mermaid 支持，等 vitepress 2.0 稳定后再添加插件
  }
});
