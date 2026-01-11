#!/usr/bin/env node
/**
 * Web Search Plugin
 *
 * A cross-language plugin example using Cerise SDK (Node.js).
 */

const path = require('path');

// Load SDK (in real deployment, SDK would be installed as npm package)
const { BasePlugin, runPlugin } = require(
  path.join(__dirname, '../../sdk/nodejs/cerise-plugin.js'),
);

class WebSearchPlugin extends BasePlugin {
  constructor() {
    super();
    this.apiKey = null;
  }

  getAbilities() {
    return [
      {
        name: 'web_search',
        description: '搜索网页内容',
        parameters: {
          type: 'object',
          properties: {
            query: {
              type: 'string',
              description: '搜索查询',
            },
            count: {
              type: 'integer',
              default: 5,
              description: '返回结果数量',
            },
          },
          required: ['query'],
        },
      },
    ];
  }

  async onInitialize(config) {
    this.config = config;
    this.apiKey = config.api_key || null;
    return true;
  }

  async execute(ability, params, context) {
    if (ability !== 'web_search') {
      return {
        success: false,
        error: `Unknown ability: ${ability}`,
      };
    }

    const query = params.query || '';
    const count = params.count || 5;

    if (!query) {
      return {
        success: false,
        error: '缺少搜索查询',
      };
    }

    // Simulated search results (replace with actual API call)
    const results = [];
    for (let i = 0; i < count; i++) {
      results.push({
        title: `搜索结果 ${i + 1}: ${query}`,
        url: `https://example.com/search?q=${encodeURIComponent(query)}&page=${i + 1}`,
        snippet: `这是关于 "${query}" 的搜索结果摘要...`,
      });
    }

    return {
      success: true,
      data: {
        query,
        count: results.length,
        results,
      },
      emotion_hint: results.length > 0 ? 'satisfied' : 'curious',
    };
  }
}

// Run plugin
const plugin = new WebSearchPlugin();
runPlugin(plugin);
