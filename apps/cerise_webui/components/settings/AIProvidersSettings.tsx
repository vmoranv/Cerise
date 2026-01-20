'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Label } from '@/components/ui/Label';
import { Dialog, DialogContent } from '@/components/ui/Dialog';
import { Switch } from '@/components/ui/Switch';
import { adminApi } from '@/lib/api';
import type { AppConfig, ProviderConfig } from '@/types/api';
import {
  Plus,
  Trash2,
  Edit2,
  Play,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';

export function AIProvidersSettings() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [loading, setLoading] = useState(true);

  // Dialog State
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingProvider, setEditingProvider] = useState<
    Partial<ProviderConfig>
  >({});
  const [isTestLoading, setIsTestLoading] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [appConfig, providersList] = await Promise.all([
        adminApi.getConfig(),
        adminApi.listProviders(),
      ]);
      setConfig(appConfig);
      setProviders(providersList);

      // Also ensure existing providers in AppConfig are up to date if they differ?
      // Usually getConfig returns the active config, listProviders returns the detailed list.
      // We'll trust listProviders for the list.
    } catch (error) {
      console.error('Failed to load data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGlobalSave = async () => {
    if (!config) return;
    try {
      await adminApi.updateConfig(config);
      // maybe show toast
    } catch (error) {
      console.error('Failed to update config:', error);
    }
  };

  const handleAddProvider = () => {
    setEditingProvider({
      enabled: true,
      type: 'openai',
      models: [],
    });
    setTestResult(null);
    setIsDialogOpen(true);
  };

  const handleEditProvider = (provider: ProviderConfig) => {
    setEditingProvider({ ...provider });
    setTestResult(null);
    setIsDialogOpen(true);
  };

  const handleSaveProvider = async () => {
    if (!editingProvider.id || !editingProvider.type) return;

    try {
      if (
        providers.some(
          (p) =>
            p.id === editingProvider.id &&
            editingProvider.id !== editingProvider.id,
        )
      ) {
        // ID conflict logic?
        // For now assume update if exists, add if not.
        // Actually ID should be unique.
      }

      const providerData = editingProvider as ProviderConfig;

      // Update or Add?
      // Check if ID exists in current list
      const exists = providers.some((p) => p.id === providerData.id);

      if (exists) {
        await adminApi.updateProvider(providerData.id, providerData);
      } else {
        await adminApi.addProvider(providerData);
      }

      setIsDialogOpen(false);
      fetchData(); // Refresh list
    } catch (error) {
      console.error('Failed to save provider:', error);
    }
  };

  const handleDeleteProvider = async (id: string) => {
    if (!confirm('Are you sure you want to delete this provider?')) return;
    try {
      await adminApi.deleteProvider(id);
      fetchData();
    } catch (error) {
      console.error('Failed to delete provider:', error);
    }
  };

  const handleTestProvider = async () => {
    if (!editingProvider.id) return;
    setIsTestLoading(true);
    try {
      // Logic: must save before test? Backend usually requires it to be in config?
      // Or maybe we can test a config payload?
      // The API `testProvider` takes `provider_id`. So it MUST be saved first?
      // Let's assume we save first if it's new, or warn user.
      // For now, let's just try calling test.
      // If unsaved, it might fail.
      const res = await adminApi.testProvider(editingProvider.id);
      setTestResult({ success: res.success, message: res.message });
    } catch (error) {
      setTestResult({
        success: false,
        message: 'Test failed (save provider first?)',
      });
    } finally {
      setIsTestLoading(false);
    }
  };

  if (loading)
    return (
      <div className="p-8 text-center animate-pulse">Loading settings...</div>
    );
  if (!config) return null;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Global AI Defaults */}
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Global Defaults</h2>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label>Default Provider</Label>
              <Select
                value={config.ai.default_provider}
                onValueChange={(val) =>
                  setConfig({
                    ...config,
                    ai: { ...config.ai, default_provider: val },
                  })
                }
                options={providers.map((p) => ({ value: p.id, label: p.name }))}
              />
            </div>
            <div className="space-y-2">
              <Label>Default Model</Label>
              <Input
                value={config.ai.default_model}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    ai: { ...config.ai, default_model: e.target.value },
                  })
                }
                placeholder="e.g. gpt-4o"
              />
            </div>
            <div className="space-y-2">
              <Label>Temperature ({config.ai.temperature})</Label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={config.ai.temperature || 0.7}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    ai: {
                      ...config.ai,
                      temperature: parseFloat(e.target.value),
                    },
                  })
                }
                className="w-full"
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button onClick={handleGlobalSave}>Save Defaults</Button>
          </div>
        </CardContent>
      </Card>

      {/* Providers List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">Providers</h2>
          <Button onClick={handleAddProvider} size="sm">
            <Plus className="w-4 h-4 mr-2" />
            Add Provider
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {providers.map((provider) => (
            <Card key={provider.id} className="group relative overflow-hidden">
              <div
                className={`absolute top-0 left-0 w-1 h-full ${provider.enabled ? 'bg-success' : 'bg-zinc-300 dark:bg-zinc-700'}`}
              />
              <CardContent className="flex flex-col h-full justify-between gap-4 p-5">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-lg">{provider.name}</h3>
                    <p className="text-sm text-foreground-tertiary font-mono">
                      {provider.type}
                    </p>
                  </div>
                  <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleEditProvider(provider)}
                      className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full"
                    >
                      <Edit2 className="w-4 h-4 text-info" />
                    </button>
                    <button
                      onClick={() => handleDeleteProvider(provider.id)}
                      className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full"
                    >
                      <Trash2 className="w-4 h-4 text-error" />
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs text-foreground-tertiary">
                  <span
                    className={`px-2 py-0.5 rounded-full ${provider.enabled ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-zinc-100 text-zinc-500'}`}
                  >
                    {provider.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                  {provider.default_model && (
                    <span>Def: {provider.default_model}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Edit/Add Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent
          title={editingProvider.id ? 'Edit Provider' : 'Add Provider'}
          onClose={() => setIsDialogOpen(false)}
        >
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>ID (Unique)</Label>
                <Input
                  disabled={
                    !!(
                      providers.find((p) => p.id === editingProvider.id) &&
                      editingProvider.id
                    )
                  }
                  value={editingProvider.id || ''}
                  onChange={(e) =>
                    setEditingProvider({
                      ...editingProvider,
                      id: e.target.value,
                    })
                  }
                  placeholder="openai-main"
                />
              </div>
              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  value={editingProvider.name || ''}
                  onChange={(e) =>
                    setEditingProvider({
                      ...editingProvider,
                      name: e.target.value,
                    })
                  }
                  placeholder="My OpenAI"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Type</Label>
              <Select
                value={editingProvider.type || 'openai'}
                onValueChange={(val) =>
                  setEditingProvider({ ...editingProvider, type: val })
                }
                options={[
                  { value: 'openai', label: 'OpenAI Compatibility' },
                  { value: 'claude', label: 'Anthropic Claude' },
                  { value: 'gemini', label: 'Google Gemini' },
                  { value: 'ollama', label: 'Ollama' },
                ]}
              />
            </div>

            <div className="space-y-2">
              <Label>Base URL (Optional)</Label>
              <Input
                value={editingProvider.base_url || ''}
                onChange={(e) =>
                  setEditingProvider({
                    ...editingProvider,
                    base_url: e.target.value,
                  })
                }
                placeholder="https://api.openai.com/v1"
              />
            </div>

            <div className="space-y-2">
              <Label>API Key</Label>
              <Input
                type="password"
                value={editingProvider.api_key || ''}
                onChange={(e) =>
                  setEditingProvider({
                    ...editingProvider,
                    api_key: e.target.value,
                  })
                }
                placeholder="sk-..."
              />
            </div>

            <div className="flex items-center gap-2 pt-2">
              <Switch
                checked={editingProvider.enabled ?? true}
                onCheckedChange={(checked) =>
                  setEditingProvider({ ...editingProvider, enabled: checked })
                }
              />
              <Label>Enabled</Label>
            </div>

            {testResult && (
              <div
                className={`p-3 rounded-lg text-sm flex items-center gap-2 ${testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}
              >
                {testResult.success ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <AlertCircle className="w-4 h-4" />
                )}
                {testResult.message}
              </div>
            )}

            <div className="flex justify-between pt-4">
              <Button
                type="button"
                variant="secondary"
                onClick={handleTestProvider}
                isLoading={isTestLoading}
              >
                Test Connection
              </Button>
              <Button onClick={handleSaveProvider}>Save Provider</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
