// Cerise Plugin SDK for C++
//
// This header expects a JSON library such as nlohmann/json.
// It implements the newline-delimited JSON-RPC protocol over stdio.
#pragma once

#include <iostream>
#include <optional>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

namespace cerise {

struct AbilityContext {
  std::string user_id;
  std::string session_id;
  std::vector<std::string> permissions;
};

struct AbilityResult {
  bool success{false};
  nlohmann::json data{};
  std::optional<std::string> error{};
  std::optional<std::string> emotion_hint{};

  nlohmann::json to_json() const {
    nlohmann::json j;
    j["success"] = success;
    if (!data.is_null()) j["data"] = data;
    if (error) j["error"] = *error;
    if (emotion_hint) j["emotion_hint"] = *emotion_hint;
    return j;
  }
};

class Plugin {
 public:
  virtual ~Plugin() = default;
  virtual std::vector<nlohmann::json> get_abilities() = 0;
  virtual bool on_initialize(const nlohmann::json& config) { (void)config; return true; }
  virtual void on_shutdown() {}
  virtual AbilityResult execute(const std::string& ability, const nlohmann::json& params,
                                const AbilityContext& ctx) = 0;
};

inline AbilityContext parse_context(const nlohmann::json& ctx) {
  AbilityContext out;
  out.user_id = ctx.value("user_id", "");
  out.session_id = ctx.value("session_id", "");
  if (ctx.contains("permissions") && ctx["permissions"].is_array()) {
    for (const auto& item : ctx["permissions"]) {
      if (item.is_string()) out.permissions.push_back(item.get<std::string>());
    }
  }
  return out;
}

inline int run(Plugin& plugin) {
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.empty()) continue;

    nlohmann::json req;
    try {
      req = nlohmann::json::parse(line);
    } catch (const std::exception& e) {
      nlohmann::json resp = {{"jsonrpc", "2.0"},
                             {"error", {{"code", -32700}, {"message", std::string("Parse error: ") + e.what()}}},
                             {"id", nullptr}};
      std::cout << resp.dump() << std::endl;
      continue;
    }

    const auto method = req.value("method", "");
    const auto id = req.contains("id") ? req["id"] : nlohmann::json(nullptr);
    const bool is_notification = id.is_null();
    const auto params = req.value("params", nlohmann::json::object());

    auto reply = [&](const nlohmann::json& result) {
      if (is_notification) return;
      nlohmann::json resp = {{"jsonrpc", "2.0"}, {"result", result}, {"id", id}};
      std::cout << resp.dump() << std::endl;
    };

    auto reply_error = [&](int code, const std::string& message) {
      if (is_notification) return;
      nlohmann::json resp = {{"jsonrpc", "2.0"}, {"error", {{"code", code}, {"message", message}}}, {"id", id}};
      std::cout << resp.dump() << std::endl;
    };

    if (method == "initialize") {
      const auto config = params.value("config", nlohmann::json::object());
      const bool ok = plugin.on_initialize(config);
      const auto abilities = plugin.get_abilities();
      reply({{"success", ok}, {"abilities", abilities}, {"skills", abilities}, {"tools", abilities}});
      continue;
    }

    if (method == "execute") {
      std::string ability = params.value("ability", "");
      if (ability.empty()) ability = params.value("skill", "");
      if (ability.empty()) ability = params.value("tool", "");
      if (ability.empty()) ability = params.value("name", "");

      const auto exec_params =
          params.contains("params") ? params["params"] : params.value("arguments", nlohmann::json::object());
      const auto ctx = parse_context(params.value("context", nlohmann::json::object()));

      auto res = plugin.execute(ability, exec_params, ctx);
      reply(res.to_json());
      continue;
    }

    if (method == "health") {
      reply({{"healthy", true}});
      continue;
    }

    if (method == "shutdown") {
      plugin.on_shutdown();
      reply({{"success", true}});
      break;
    }

    reply_error(-32601, "Method not found");
  }

  return 0;
}

}  // namespace cerise

