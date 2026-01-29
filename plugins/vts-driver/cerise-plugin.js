/**
 * Cerise Plugin SDK for Node.js
 *
 * Use this SDK to create plugins that communicate with Cerise Core.
 */

const readline = require('readline');

/**
 * @typedef {Object} AbilityContext
 * @property {string} user_id
 * @property {string} session_id
 * @property {string[]} permissions
 */

/**
 * @typedef {Object} AbilityResult
 * @property {boolean} success
 * @property {any} data
 * @property {string|null} error
 * @property {string|null} emotion_hint
 */

/**
 * Base class for Cerise plugins
 * @abstract
 */
class BasePlugin {
  constructor() {
    /** @type {Object} */
    this.config = {};
    /** @type {string[]} */
    this.permissions = [];
  }

  /**
   * Return list of abilities provided by this plugin
   * @abstract
   * @returns {Array<{name: string, description: string, parameters: Object}>}
   */
  getAbilities() {
    throw new Error('getAbilities() must be implemented');
  }

  /**
   * Execute an ability
   * @abstract
   * @param {string} ability - Ability name
   * @param {Object} params - Parameters
   * @param {AbilityContext} context - Execution context
   * @returns {Promise<AbilityResult>}
   */
  async execute(ability, params, context) {
    throw new Error('execute() must be implemented');
  }

  /**
   * Called when plugin is initialized
   * @param {Object} config - Configuration
   * @returns {Promise<boolean>}
   */
  async onInitialize(config) {
    this.config = config;
    return true;
  }

  /**
   * Called when plugin is shutting down
   * @returns {Promise<void>}
   */
  async onShutdown() {}
}

/**
 * Runs a plugin and handles JSON-RPC communication
 */
class PluginRunner {
  /**
   * @param {BasePlugin} plugin
   */
  constructor(plugin) {
    this.plugin = plugin;
    this._running = false;
    this._rl = null;
  }

  /**
   * Main loop: read from stdin, write to stdout
   * @returns {Promise<void>}
   */
  async run() {
    this._running = true;

    this._rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: false,
    });

    for await (const line of this._rl) {
      if (!this._running) break;

      try {
        const request = JSON.parse(line.trim());
        const response = await this._handleRequest(request);

        if (response) {
          console.log(JSON.stringify(response));
        }
      } catch (e) {
        if (e instanceof SyntaxError) {
          const errorResponse = {
            jsonrpc: '2.0',
            error: { code: -32700, message: `Parse error: ${e.message}` },
            id: null,
          };
          console.log(JSON.stringify(errorResponse));
        } else {
          const errorResponse = {
            jsonrpc: '2.0',
            error: { code: -32603, message: `Internal error: ${e.message}` },
            id: null,
          };
          console.log(JSON.stringify(errorResponse));
        }
      }
    }
  }

  /**
   * Handle a JSON-RPC request
   * @param {Object} request
   * @returns {Promise<Object|null>}
   */
  async _handleRequest(request) {
    const method = request.method || '';
    const params = request.params || {};
    const reqId = request.id;

    const isNotification = reqId === undefined || reqId === null;

    try {
      const result = await this._dispatch(method, params);
      if (isNotification) return null;
      return {
        jsonrpc: '2.0',
        result,
        id: reqId,
      };
    } catch (e) {
      if (isNotification) return null;
      return {
        jsonrpc: '2.0',
        error: { code: -32603, message: e.message },
        id: reqId,
      };
    }
  }

  /**
   * Dispatch to appropriate handler
   * @param {string} method
   * @param {Object} params
   * @returns {Promise<any>}
   */
  async _dispatch(method, params) {
    switch (method) {
      case 'initialize': {
        const config = params.config || {};
        this.plugin.permissions = params.permissions || [];
        const success = await this.plugin.onInitialize(config);
        const abilities = this.plugin.getAbilities();
        return {
          success,
          abilities,
          skills: abilities,
          tools: abilities,
        };
      }

      case 'execute': {
        const ability = params.ability || params.skill || params.tool || params.name || '';
        const execParams = params.params ?? params.arguments ?? {};
        const contextData = params.context || {};

        const context = {
          user_id: contextData.user_id || '',
          session_id: contextData.session_id || '',
          permissions: contextData.permissions || [],
        };

        const result = await this.plugin.execute(ability, execParams, context);
        return {
          success: result.success,
          data: result.data,
          error: result.error,
          emotion_hint: result.emotion_hint,
        };
      }

      case 'health':
        return { healthy: true };

      case 'shutdown':
        await this.plugin.onShutdown();
        this._running = false;
        if (this._rl) this._rl.close();
        return { success: true };

      default:
        throw new Error(`Unknown method: ${method}`);
    }
  }

  /**
   * Send an event notification to Core
   * @param {string} eventType
   * @param {Object} data
   */
  sendEvent(eventType, data) {
    const notification = {
      jsonrpc: '2.0',
      method: 'event',
      params: { type: eventType, data },
    };
    console.log(JSON.stringify(notification));
  }

  /**
   * Send a log message to Core
   * @param {string} level
   * @param {string} message
   */
  log(level, message) {
    const notification = {
      jsonrpc: '2.0',
      method: 'log',
      params: { level, message },
    };
    console.log(JSON.stringify(notification));
  }
}

/**
 * Run a plugin (blocking)
 * @param {BasePlugin} plugin
 */
function runPlugin(plugin) {
  const runner = new PluginRunner(plugin);
  runner.run().catch((e) => {
    console.error('Plugin error:', e);
    process.exit(1);
  });
}

module.exports = {
  BasePlugin,
  PluginRunner,
  runPlugin,
};
