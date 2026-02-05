#!/usr/bin/env node

const path = require('path');

// In-repo development: load SDK by relative path.
const { BasePlugin, runPlugin } = require(path.join(
  __dirname,
  '../../sdk/nodejs/cerise-plugin.js',
));

class EchoNodePlugin extends BasePlugin {
  constructor() {
    super();
    this.prefix = '';
  }

  getAbilities() {
    return [
      {
        name: 'echo_node',
        description: 'Echo text back (optionally with a prefix from config).',
        parameters: {
          type: 'object',
          properties: {
            text: { type: 'string', description: 'Text to echo' },
          },
          required: ['text'],
        },
      },
    ];
  }

  async onInitialize(config) {
    this.config = config || {};
    this.prefix = String(this.config.prefix || '');
    return true;
  }

  async execute(ability, params, context) {
    if (ability !== 'echo_node') {
      return { success: false, error: `Unknown ability: ${ability}` };
    }

    const text = String((params || {}).text || '');
    return {
      success: true,
      data: { text: `${this.prefix}${text}` },
      error: null,
      emotion_hint: 'satisfied',
    };
  }
}

runPlugin(new EchoNodePlugin());
