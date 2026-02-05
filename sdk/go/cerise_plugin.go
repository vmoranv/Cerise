// Cerise Plugin SDK for Go
//
// This SDK implements the newline-delimited JSON-RPC protocol used by Cerise Core.
// A plugin runs as a subprocess (stdio transport) and responds to:
// - initialize
// - execute
// - health
// - shutdown
package ceriseplugin

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
)

type AbilityContext struct {
	UserID      string   `json:"user_id"`
	SessionID   string   `json:"session_id"`
	Permissions []string `json:"permissions"`
}

type AbilityResult struct {
	Success     bool        `json:"success"`
	Data        any         `json:"data,omitempty"`
	Error       *string     `json:"error,omitempty"`
	EmotionHint *string     `json:"emotion_hint,omitempty"`
}

type Ability struct {
	Name        string         `json:"name"`
	Description string         `json:"description,omitempty"`
	Parameters  map[string]any `json:"parameters,omitempty"`
}

type Plugin interface {
	GetAbilities() []Ability
	OnInitialize(config map[string]any) error
	Execute(ability string, params map[string]any, ctx AbilityContext) (AbilityResult, error)
	OnShutdown() error
}

type jsonrpcRequest struct {
	JSONRPC string         `json:"jsonrpc"`
	Method  string         `json:"method"`
	Params  map[string]any `json:"params,omitempty"`
	ID      any            `json:"id,omitempty"`
}

type jsonrpcResponse struct {
	JSONRPC string         `json:"jsonrpc"`
	Result  any            `json:"result,omitempty"`
	Error   *jsonrpcError  `json:"error,omitempty"`
	ID      any            `json:"id,omitempty"`
}

type jsonrpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func Run(plugin Plugin) error {
	in := bufio.NewScanner(os.Stdin)
	// Allow larger payloads than the default 64K.
	in.Buffer(make([]byte, 0, 1024*1024), 8*1024*1024)

	out := bufio.NewWriter(os.Stdout)
	defer out.Flush()

	running := true
	for running && in.Scan() {
		line := in.Bytes()
		if len(line) == 0 {
			continue
		}

		var req jsonrpcRequest
		if err := json.Unmarshal(line, &req); err != nil {
			resp := jsonrpcResponse{
				JSONRPC: "2.0",
				Error:   &jsonrpcError{Code: -32700, Message: fmt.Sprintf("Parse error: %v", err)},
				ID:      nil,
			}
			_ = writeJSON(out, resp)
			continue
		}

		// Notifications have no id; ignore response.
		isNotification := req.ID == nil

		result, rpcErr, shouldStop := dispatch(plugin, req.Method, req.Params)
		if shouldStop {
			running = false
		}

		if isNotification {
			continue
		}

		resp := jsonrpcResponse{JSONRPC: "2.0", ID: req.ID}
		if rpcErr != nil {
			resp.Error = rpcErr
		} else {
			resp.Result = result
		}

		_ = writeJSON(out, resp)
	}

	return in.Err()
}

func dispatch(plugin Plugin, method string, params map[string]any) (any, *jsonrpcError, bool) {
	switch method {
	case "initialize":
		cfg, _ := params["config"].(map[string]any)
		if cfg == nil {
			cfg = map[string]any{}
		}
		if err := plugin.OnInitialize(cfg); err != nil {
			return map[string]any{"success": false, "error": err.Error()}, nil, false
		}
		abilities := plugin.GetAbilities()
		return map[string]any{
			"success":   true,
			"abilities": abilities,
			"skills":    abilities,
			"tools":     abilities,
		}, nil, false

	case "execute":
		ability, _ := params["ability"].(string)
		if ability == "" {
			ability, _ = params["skill"].(string)
		}
		if ability == "" {
			ability, _ = params["tool"].(string)
		}
		if ability == "" {
			ability, _ = params["name"].(string)
		}

		execParams, _ := params["params"].(map[string]any)
		if execParams == nil {
			execParams, _ = params["arguments"].(map[string]any)
		}
		if execParams == nil {
			execParams = map[string]any{}
		}

		ctxRaw, _ := params["context"].(map[string]any)
		ctx := AbilityContext{}
		if ctxRaw != nil {
			if v, ok := ctxRaw["user_id"].(string); ok {
				ctx.UserID = v
			}
			if v, ok := ctxRaw["session_id"].(string); ok {
				ctx.SessionID = v
			}
			if v, ok := ctxRaw["permissions"].([]any); ok {
				perms := make([]string, 0, len(v))
				for _, p := range v {
					if s, ok := p.(string); ok {
						perms = append(perms, s)
					}
				}
				ctx.Permissions = perms
			}
		}

		res, err := plugin.Execute(ability, execParams, ctx)
		if err != nil {
			msg := err.Error()
			res.Success = false
			res.Error = &msg
		}
		return res, nil, false

	case "health":
		return map[string]any{"healthy": true}, nil, false

	case "shutdown":
		_ = plugin.OnShutdown()
		return map[string]any{"success": true}, nil, true

	default:
		return nil, &jsonrpcError{Code: -32601, Message: "Method not found"}, false
	}
}

func writeJSON(w *bufio.Writer, v any) error {
	b, err := json.Marshal(v)
	if err != nil {
		return err
	}
	_, err = w.Write(append(b, '\n'))
	if err != nil {
		return err
	}
	return w.Flush()
}

