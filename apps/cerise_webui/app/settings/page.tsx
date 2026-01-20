'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { ArrowLeft, Sliders, Cpu, User, Puzzle } from 'lucide-react';

// Import Settings Sections
import { GeneralSettings } from '@/components/settings/GeneralSettings';
import { AIProvidersSettings } from '@/components/settings/AIProvidersSettings';
import { CharacterSettings } from '@/components/settings/CharacterSettings';
import { PluginsSettings } from '@/components/settings/PluginsSettings';

export default function SettingsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState('general');

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="max-w-[1800px] mx-auto px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.push('/')}
              className="-ml-2"
            >
              <ArrowLeft className="w-5 h-5 mr-1" />
              Return
            </Button>
            <div className="h-6 w-px bg-border mx-2" />
            <h1 className="text-xl font-bold tracking-tight">Settings</h1>
          </div>
        </div>
      </header>

      <main className="max-w-[1800px] mx-auto px-8 py-10">
        <Tabs
          defaultValue="general"
          value={activeTab}
          onValueChange={setActiveTab}
        >
          <div className="mb-0 overflow-x-auto pb-2">
            {/* Removed width constraints and cleaned up classes */}
            <TabsList className="inline-flex h-auto w-auto bg-zinc-100 dark:bg-zinc-800/50 p-1 rounded-xl">
              <TabsTrigger value="general" className="gap-2 px-6 py-2.5">
                <Sliders className="w-4 h-4" />
                General
              </TabsTrigger>
              <TabsTrigger value="providers" className="gap-2 px-6 py-2.5">
                <Cpu className="w-4 h-4" />
                AI Providers
              </TabsTrigger>
              <TabsTrigger value="character" className="gap-2 px-6 py-2.5">
                <User className="w-4 h-4" />
                Character
              </TabsTrigger>
              <TabsTrigger value="plugins" className="gap-2 px-6 py-2.5">
                <Puzzle className="w-4 h-4" />
                Plugins
              </TabsTrigger>
            </TabsList>
          </div>

          <div className="animate-fade-in space-y-8 mt-8">
            <TabsContent value="general">
              <GeneralSettings />
            </TabsContent>

            <TabsContent value="providers">
              <AIProvidersSettings />
            </TabsContent>

            <TabsContent value="character">
              <CharacterSettings />
            </TabsContent>

            <TabsContent value="plugins">
              <PluginsSettings />
            </TabsContent>
          </div>
        </Tabs>
      </main>
    </div>
  );
}
