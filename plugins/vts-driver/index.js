const fs = require("fs");
const path = require("path");
const { ApiClient } = require("vtubestudio");
const WebSocket = require("ws");
const { BasePlugin, runPlugin } = require("./cerise-plugin");

const DEFAULT_CONFIG = {
  host: "127.0.0.1",
  port: 8001,
  url: "",
  pluginName: "Cerise L2D Driver",
  pluginDeveloper: "Cerise",
  authTokenPath: "auth-token.txt",
  autoCreateParameters: true,
  refreshIntervalMs: 500,
  smoothing: 0.35,
  parameterNames: {
    valence: "EmotionValence",
    arousal: "EmotionArousal",
    intensity: "EmotionIntensity",
  },
  parameterRanges: {
    valence: { min: -1, max: 1, default: 0 },
    arousal: { min: 0, max: 1, default: 0.3 },
    intensity: { min: 0, max: 1, default: 0.5 },
  },
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function toNumber(value) {
  if (value === null || value === undefined) return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

function envNumber(name) {
  const raw = process.env[name];
  if (!raw) return null;
  const num = Number(raw);
  return Number.isFinite(num) ? num : null;
}

function envString(name) {
  return process.env[name] || null;
}

function resolveConfig(config) {
  const overrides = config || {};
  const resolved = {
    ...DEFAULT_CONFIG,
    ...overrides,
    parameterNames: {
      ...DEFAULT_CONFIG.parameterNames,
      ...(overrides.parameterNames || {}),
    },
    parameterRanges: {
      ...DEFAULT_CONFIG.parameterRanges,
      ...(overrides.parameterRanges || {}),
    },
  };

  resolved.parameterRanges.valence = {
    ...DEFAULT_CONFIG.parameterRanges.valence,
    ...(resolved.parameterRanges.valence || {}),
  };
  resolved.parameterRanges.arousal = {
    ...DEFAULT_CONFIG.parameterRanges.arousal,
    ...(resolved.parameterRanges.arousal || {}),
  };
  resolved.parameterRanges.intensity = {
    ...DEFAULT_CONFIG.parameterRanges.intensity,
    ...(resolved.parameterRanges.intensity || {}),
  };

  const host = envString("VTS_HOST");
  const port = envNumber("VTS_PORT");
  const url = envString("VTS_URL");
  const pluginName = envString("VTS_PLUGIN_NAME");
  const pluginDeveloper = envString("VTS_PLUGIN_DEVELOPER");
  const authTokenPath = envString("VTS_AUTH_TOKEN_PATH");
  const smoothing = envNumber("VTS_SMOOTHING");
  const refreshIntervalMs = envNumber("VTS_REFRESH_INTERVAL_MS");

  if (host) resolved.host = host;
  if (port !== null) resolved.port = port;
  if (url) resolved.url = url;
  if (pluginName) resolved.pluginName = pluginName;
  if (pluginDeveloper) resolved.pluginDeveloper = pluginDeveloper;
  if (authTokenPath) resolved.authTokenPath = authTokenPath;
  if (smoothing !== null) resolved.smoothing = smoothing;
  if (refreshIntervalMs !== null) resolved.refreshIntervalMs = refreshIntervalMs;

  const paramValence = envString("VTS_PARAM_VALENCE");
  const paramArousal = envString("VTS_PARAM_AROUSAL");
  const paramIntensity = envString("VTS_PARAM_INTENSITY");
  if (paramValence) resolved.parameterNames.valence = paramValence;
  if (paramArousal) resolved.parameterNames.arousal = paramArousal;
  if (paramIntensity) resolved.parameterNames.intensity = paramIntensity;

  return resolved;
}

class VtsDriverPlugin extends BasePlugin {
  constructor() {
    super();
    this._api = null;
    this._connected = false;
    this._refreshTimer = null;
    this._currentValues = new Map();
    this._config = DEFAULT_CONFIG;
  }

  getAbilities() {
    return [
      {
        name: "l2d.set_emotion",
        description: "Set emotion valence/arousal/intensity parameters in VTube Studio.",
        parameters: {
          type: "object",
          properties: {
            valence: { type: "number", minimum: -1, maximum: 1 },
            arousal: { type: "number", minimum: 0, maximum: 1 },
            intensity: { type: "number", minimum: 0, maximum: 1 },
            smoothing: { type: "number", minimum: 0, maximum: 1 },
          },
          required: ["valence", "arousal", "intensity"],
        },
      },
      {
        name: "l2d.set_parameters",
        description: "Set arbitrary Live2D parameter values in VTube Studio.",
        parameters: {
          type: "object",
          properties: {
            parameters: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  id: { type: "string" },
                  value: { type: "number" },
                  weight: { type: "number", minimum: 0, maximum: 1 },
                },
                required: ["id", "value"],
              },
            },
            smoothing: { type: "number", minimum: 0, maximum: 1 },
          },
          required: ["parameters"],
        },
      },
    ];
  }

  async onInitialize(config) {
    this._config = resolveConfig(config);
    this._api = this._createClient();

    this._api.on("connect", async () => {
      this._connected = true;
      await this._ensureParameters();
    });

    this._api.on("disconnect", () => {
      this._connected = false;
    });

    this._api.on("error", (err) => {
      console.error("VTS error:", err);
    });

    this._startRefreshLoop();
    return true;
  }

  async onShutdown() {
    if (this._refreshTimer) {
      clearInterval(this._refreshTimer);
      this._refreshTimer = null;
    }
    if (this._api && this._api.isConnected) {
      await this._api.disconnect();
    }
    this._currentValues.clear();
  }

  async execute(ability, params) {
    switch (ability) {
      case "l2d.set_emotion":
        return await this._setEmotion(params || {});
      case "l2d.set_parameters":
        return await this._setParameters(params || {});
      default:
        return { success: false, error: `Unknown ability: ${ability}` };
    }
  }

  _createClient() {
    const tokenPath = path.resolve(__dirname, this._config.authTokenPath || "auth-token.txt");
    const authTokenGetter = () => {
      try {
        if (!fs.existsSync(tokenPath)) return "";
        return fs.readFileSync(tokenPath, "utf-8").trim();
      } catch {
        return "";
      }
    };
    const authTokenSetter = (token) => {
      try {
        fs.writeFileSync(tokenPath, token, { encoding: "utf-8" });
      } catch (err) {
        console.error("Failed to save auth token:", err);
      }
    };

    const url = this._config.url && this._config.url.length > 0
      ? this._config.url
      : `ws://${this._config.host}:${this._config.port}`;

    return new ApiClient({
      pluginName: this._config.pluginName,
      pluginDeveloper: this._config.pluginDeveloper,
      authTokenGetter,
      authTokenSetter,
      url,
      webSocketFactory: (wsUrl) => new WebSocket(wsUrl),
    });
  }

  _startRefreshLoop() {
    if (this._refreshTimer) return;
    const interval = Math.max(200, Number(this._config.refreshIntervalMs) || 500);
    this._refreshTimer = setInterval(() => {
      this._sendCurrentValues().catch(() => {});
    }, interval);
  }

  async _ensureParameters() {
    if (!this._config.autoCreateParameters || !this._api) return;

    const defs = this._parameterDefinitions();
    for (const def of defs) {
      try {
        await this._api.parameterCreation(def);
      } catch (err) {
        // Ignore if already exists or invalid; VTS will report details in logs.
        console.warn("Parameter creation failed:", def.parameterName, err?.message || err);
      }
    }
  }

  _parameterDefinitions() {
    const names = this._config.parameterNames;
    const ranges = this._config.parameterRanges;
    return [
      {
        parameterName: names.valence,
        explanation: "Emotion valence (-1 to 1).",
        min: ranges.valence.min,
        max: ranges.valence.max,
        defaultValue: ranges.valence.default,
      },
      {
        parameterName: names.arousal,
        explanation: "Emotion arousal (0 to 1).",
        min: ranges.arousal.min,
        max: ranges.arousal.max,
        defaultValue: ranges.arousal.default,
      },
      {
        parameterName: names.intensity,
        explanation: "Emotion intensity (0 to 1).",
        min: ranges.intensity.min,
        max: ranges.intensity.max,
        defaultValue: ranges.intensity.default,
      },
    ];
  }

  _resolveSmoothing(requested, intensity) {
    const candidate = toNumber(requested);
    if (candidate !== null) return clamp(candidate, 0, 1);

    const base = clamp(Number(this._config.smoothing) || 0, 0, 1);
    const intensityValue = toNumber(intensity);
    if (intensityValue === null) return base;

    return clamp(base * (1 - clamp(intensityValue, 0, 1)), 0, 1);
  }

  async _setEmotion(params) {
    const valence = toNumber(params.valence);
    const arousal = toNumber(params.arousal);
    const intensity = toNumber(params.intensity);

    if (valence === null || arousal === null || intensity === null) {
      return { success: false, error: "Missing valence, arousal, or intensity" };
    }

    const smoothing = this._resolveSmoothing(params.smoothing, intensity);
    const names = this._config.parameterNames;
    const updates = [
      {
        id: names.valence,
        value: clamp(valence, -1, 1),
      },
      {
        id: names.arousal,
        value: clamp(arousal, 0, 1),
      },
      {
        id: names.intensity,
        value: clamp(intensity, 0, 1),
      },
    ];

    return await this._applyParameters(updates, smoothing);
  }

  async _setParameters(params) {
    const list = Array.isArray(params.parameters) ? params.parameters : [];
    if (!list.length) {
      return { success: false, error: "No parameters provided" };
    }

    const smoothing = this._resolveSmoothing(params.smoothing, null);
    const updates = [];
    for (const entry of list) {
      const id = entry?.id;
      const value = toNumber(entry?.value);
      if (!id || value === null) continue;
      updates.push({
        id,
        value,
        weight: toNumber(entry?.weight),
      });
    }

    if (!updates.length) {
      return { success: false, error: "No valid parameters to update" };
    }

    return await this._applyParameters(updates, smoothing);
  }

  async _applyParameters(updates, smoothing) {
    this._updateCurrentValues(updates, smoothing);
    await this._sendCurrentValues();

    return {
      success: true,
      data: {
        updated: updates.map((item) => ({ id: item.id, value: item.value })),
      },
    };
  }

  _updateCurrentValues(updates, smoothing) {
    const blend = 1 - clamp(smoothing, 0, 1);
    for (const update of updates) {
      const prev = this._currentValues.get(update.id);
      const prevValue = prev ? prev.value : update.value;
      const nextValue = prevValue + (update.value - prevValue) * blend;
      const weight = update.weight !== null && update.weight !== undefined
        ? clamp(update.weight, 0, 1)
        : prev?.weight ?? 1;
      this._currentValues.set(update.id, { value: nextValue, weight });
    }
  }

  async _sendCurrentValues() {
    if (!this._api || !this._api.isConnected || this._currentValues.size === 0) {
      return;
    }

    const parameterValues = [];
    for (const [id, data] of this._currentValues.entries()) {
      parameterValues.push({ id, value: data.value, weight: data.weight });
    }

    try {
      await this._api.injectParameterData({
        mode: "set",
        parameterValues,
      });
    } catch (err) {
      console.warn("InjectParameterData failed:", err?.message || err);
    }
  }
}

runPlugin(new VtsDriverPlugin());
