'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Label } from '@/components/ui/Label';
import { adminApi } from '@/lib/api';
import type { AppConfig } from '@/types/api';

export function GeneralSettings() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getConfig();
      setConfig(data);
    } catch (error) {
      console.error('Failed to load config:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config) return;
    try {
      setSaving(true);
      await adminApi.updateConfig(config);
    } catch (error) {
      console.error('Failed to save config:', error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-foreground-secondary animate-pulse">
        Loading configuration...
      </div>
    );
  }

  if (!config) return null;

  return (
    <div className="space-y-6 animate-fade-in">
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            Server Configuration
          </h2>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label>Host</Label>
              <Input
                value={config.server.host}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    server: { ...config.server, host: e.target.value },
                  })
                }
              />
            </div>
            <div className="space-y-2">
              <Label>Port</Label>
              <Input
                type="number"
                value={config.server.port}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    server: {
                      ...config.server,
                      port: parseInt(e.target.value) || 8000,
                    },
                  })
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">Logging</h2>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label>Log Level</Label>
              <Select
                value={config.logging.level}
                onValueChange={(value) =>
                  setConfig({
                    ...config,
                    logging: { ...config.logging, level: value },
                  })
                }
                options={[
                  { value: 'DEBUG', label: 'DEBUG' },
                  { value: 'INFO', label: 'INFO' },
                  { value: 'WARNING', label: 'WARNING' },
                  { value: 'ERROR', label: 'ERROR' },
                ]}
              />
            </div>
            <div className="space-y-2">
              <Label>Log File Path</Label>
              <Input
                placeholder="Leave empty to disable file logging"
                value={config.logging.file}
                onChange={(e) =>
                  setConfig({
                    ...config,
                    logging: { ...config.logging, file: e.target.value },
                  })
                }
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold">TTS Service</h2>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label>TTS Server URL</Label>
            <Input
              value={config.tts.server_url}
              onChange={(e) =>
                setConfig({
                  ...config,
                  tts: { ...config.tts, server_url: e.target.value },
                })
              }
            />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end pt-4">
        <Button onClick={handleSave} isLoading={saving} size="lg">
          Save Changes
        </Button>
      </div>
    </div>
  );
}
