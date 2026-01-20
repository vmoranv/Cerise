'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Label } from '@/components/ui/Label';
import { Switch } from '@/components/ui/Switch';
import { Dialog, DialogContent } from '@/components/ui/Dialog';
import { adminApi } from '@/lib/api';
import type { InstalledPlugin } from '@/types/api';
import { Download, Upload, Trash2, Github, Package } from 'lucide-react';

export function PluginsSettings() {
  const [plugins, setPlugins] = useState<InstalledPlugin[]>([]);
  const [loading, setLoading] = useState(true);

  // Install Dialog
  const [isInstallOpen, setIsInstallOpen] = useState(false);
  const [installTab, setInstallTab] = useState<'github' | 'upload'>('github');
  const [githubUrl, setGithubUrl] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [installing, setInstalling] = useState(false);

  useEffect(() => {
    loadPlugins();
  }, []);

  const loadPlugins = async () => {
    try {
      setLoading(true);
      const list = await adminApi.listPlugins();
      setPlugins(list);
    } catch (error) {
      console.error('Failed to load plugins:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePlugin = async (plugin: InstalledPlugin) => {
    try {
      if (plugin.enabled) {
        await adminApi.disablePlugin(plugin.name);
      } else {
        await adminApi.enablePlugin(plugin.name);
      }
      loadPlugins();
    } catch (e) {
      console.error(e);
    }
  };

  const handleUninstall = async (name: string) => {
    if (!confirm(`Uninstall plugin ${name}?`)) return;
    try {
      await adminApi.uninstallPlugin(name);
      loadPlugins();
    } catch (e) {
      console.error(e);
    }
  };

  const handleInstall = async () => {
    setInstalling(true);
    try {
      if (installTab === 'github') {
        await adminApi.installPluginFromGithub(githubUrl);
      } else if (installTab === 'upload' && uploadFile) {
        const formData = new FormData();
        formData.append('file', uploadFile);
        await adminApi.installPluginFromFile(formData);
      }
      setIsInstallOpen(false);
      setGithubUrl('');
      setUploadFile(null);
      loadPlugins();
    } catch (e) {
      console.error('Install failed:', e);
      alert('Installation failed. Check console.');
    } finally {
      setInstalling(false);
    }
  };

  if (loading)
    return (
      <div className="p-8 text-center animate-pulse">Loading plugins...</div>
    );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Installed Plugins</h2>
        <Button onClick={() => setIsInstallOpen(true)}>
          <Download className="w-4 h-4 mr-2" />
          Install Plugin
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {plugins.length === 0 && (
          <div className="text-center p-8 border border-dashed rounded-xl border-border text-foreground-tertiary">
            No plugins installed.
          </div>
        )}
        {plugins.map((plugin) => (
          <Card
            key={plugin.name}
            className="flex flex-row items-center justify-between p-6"
          >
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-lg bg-cerise-light/10 flex items-center justify-center text-cerise-primary">
                <Package className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">{plugin.name}</h3>
                <div className="flex items-center gap-2 text-sm text-foreground-secondary">
                  <span className="bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded text-xs">
                    v{plugin.version}
                  </span>
                  {plugin.author && <span>by {plugin.author}</span>}
                </div>
                {plugin.description && (
                  <p className="text-sm text-foreground-tertiary mt-1">
                    {plugin.description}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <span
                  className={`text-sm ${plugin.enabled ? 'text-green-600' : 'text-zinc-500'}`}
                >
                  {plugin.enabled ? 'Enabled' : 'Disabled'}
                </span>
                <Switch
                  checked={plugin.enabled}
                  onCheckedChange={() => handleTogglePlugin(plugin)}
                />
              </div>
              <button
                onClick={() => handleUninstall(plugin.name)}
                className="p-2 text-foreground-tertiary hover:text-error hover:bg-error/10 rounded-lg transition-colors"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </Card>
        ))}
      </div>

      <Dialog open={isInstallOpen} onOpenChange={setIsInstallOpen}>
        <DialogContent title="Install Plugin">
          <div className="space-y-6">
            <div className="flex p-1 bg-zinc-100 dark:bg-zinc-800 rounded-lg">
              <button
                className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${installTab === 'github' ? 'bg-white dark:bg-zinc-700 shadow-sm' : 'text-foreground-secondary'}`}
                onClick={() => setInstallTab('github')}
              >
                From GitHub
              </button>
              <button
                className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${installTab === 'upload' ? 'bg-white dark:bg-zinc-700 shadow-sm' : 'text-foreground-secondary'}`}
                onClick={() => setInstallTab('upload')}
              >
                Upload Zip
              </button>
            </div>

            {installTab === 'github' ? (
              <div className="space-y-3">
                <Label>GitHub Repository URL</Label>
                <div className="relative">
                  <Github className="absolute left-3 top-3 w-5 h-5 text-foreground-tertiary" />
                  <Input
                    className="pl-10"
                    placeholder="https://github.com/user/repo"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                  />
                </div>
                <p className="text-xs text-foreground-tertiary">
                  Plugin will be cloned from the main branch.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <Label>Plugin ZIP File</Label>
                <div className="border-2 border-dashed border-border rounded-lg p-8 text-center hover:border-cerise-light/50 transition-colors cursor-pointer relative">
                  <input
                    type="file"
                    accept=".zip"
                    className="absolute inset-0 opacity-0 cursor-pointer"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  />
                  <Upload className="w-8 h-8 mx-auto text-foreground-tertiary mb-2" />
                  <p className="text-sm font-medium">
                    {uploadFile
                      ? uploadFile.name
                      : 'Click to upload or drag and drop'}
                  </p>
                  <p className="text-xs text-foreground-tertiary mt-1">
                    .zip files only
                  </p>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Button variant="ghost" onClick={() => setIsInstallOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleInstall} isLoading={installing}>
                {installTab === 'github'
                  ? 'Clone & Install'
                  : 'Upload & Install'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
