'use client';

import { useState, useEffect } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { Label } from '@/components/ui/Label';
import { adminApi } from '@/lib/api';
import type { CharacterConfig, PersonalityTraits } from '@/types/api';

export function CharacterSettings() {
  const [characters, setCharacters] = useState<string[]>([]);
  const [activeCharName, setActiveCharName] = useState<string>('default');
  const [config, setConfig] = useState<CharacterConfig | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadList();
  }, []);

  // When active char changes, load its config
  useEffect(() => {
    if (activeCharName) {
      loadCharacter(activeCharName);
    }
  }, [activeCharName]);

  const loadList = async () => {
    try {
      const list = await adminApi.listCharacters();
      setCharacters(list);
      // If list has items and no active char, set first
      if (list.length > 0 && activeCharName === 'default') {
        // Should we use the AppConfig active character?
        // For now, just list.
      }
    } catch (e) {
      console.error('Failed to list chars', e);
    }
  };

  const loadCharacter = async (name: string) => {
    try {
      setLoading(true);
      const data = await adminApi.getCharacter(name);
      setConfig(data);
    } catch (error) {
      console.error('Failed to load character:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!config || !activeCharName) return;
    try {
      setSaving(true);
      await adminApi.updateCharacter(activeCharName, config);
    } catch (error) {
      console.error('Failed to save character:', error);
    } finally {
      setSaving(false);
    }
  };

  const updatePersonality = (key: keyof PersonalityTraits, value: number) => {
    if (!config) return;
    setConfig({
      ...config,
      personality: {
        ...config.personality,
        [key]: value,
      },
    });
  };

  if (!config && loading)
    return (
      <div className="p-8 text-center animate-pulse">Loading character...</div>
    );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-4">
        <Label>Select Character to Edit:</Label>
        <div className="w-64">
          <Select
            value={activeCharName}
            onValueChange={setActiveCharName}
            options={characters.map((c) => ({ value: c, label: c }))}
          />
        </div>
      </div>

      {config && (
        <>
          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">Basic Info</h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input
                    value={config.name}
                    onChange={(e) =>
                      setConfig({ ...config, name: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Language</Label>
                  <Input
                    value={config.language}
                    onChange={(e) =>
                      setConfig({ ...config, language: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>System Prompt Template</Label>
                <textarea
                  className="w-full h-32 rounded-lg border border-border bg-white dark:bg-zinc-900 p-3 text-sm focus:ring-2 focus:ring-cerise-light outline-none"
                  value={config.system_prompt_template || ''}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      system_prompt_template: e.target.value,
                    })
                  }
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-lg font-semibold">Personality Traits</h2>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {Object.entries(config.personality).map(([trait, value]) => {
                // Skip if not number (though type enforcement matches)
                if (typeof value !== 'number') return null;
                return (
                  <div key={trait} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="capitalize">{trait}</span>
                      <span className="font-mono text-cerise-primary">
                        {value.toFixed(1)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.1"
                      value={value}
                      onChange={(e) =>
                        updatePersonality(
                          trait as keyof PersonalityTraits,
                          parseFloat(e.target.value),
                        )
                      }
                      className="w-full accent-cerise-primary h-2 bg-zinc-200 rounded-lg appearance-none cursor-pointer dark:bg-zinc-700"
                    />
                  </div>
                );
              })}
            </CardContent>
          </Card>

          <div className="flex justify-end pt-4">
            <Button onClick={handleSave} isLoading={saving} size="lg">
              Save Character
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
