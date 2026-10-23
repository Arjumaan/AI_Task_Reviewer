import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { LoginView } from './views/LoginView';
import { AssignerDashboard } from './views/AssignerDashboard';
import { InternDashboard } from './views/InternDashboard';
import { AdminDashboard } from './views/AdminDashboard';
import { AudioVoiceRoom } from './components/AudioVoiceRoom';

const MainLayout: React.FC = () => {
  const { user, isLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<'dashboard' | 'system'>('dashboard');
  const [voiceRoomOpen, setVoiceRoomOpen] = useState(false);
  const [voiceRoomTitle, setVoiceRoomTitle] = useState('Task Briefing Session');
  const [voiceRoomTaskId, setVoiceRoomTaskId] = useState<string | undefined>(undefined);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm">Connecting to local workspace...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginView />;
  }

  const handleOpenVoiceRoom = (taskTitle?: string, taskId?: string) => {
    if (taskTitle) setVoiceRoomTitle(taskTitle);
    if (taskId) setVoiceRoomTaskId(taskId);
    setVoiceRoomOpen(true);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar
        onOpenVoiceRoom={() => handleOpenVoiceRoom()}
        activeTab={activeTab}
        setActiveTab={(tab: string) => setActiveTab(tab as any)}
      />

      <main className="flex-1">
        {activeTab === 'system' && user.role === 'ADMIN' ? (
          <AdminDashboard />
        ) : user.role === 'INTERN' ? (
          <InternDashboard onOpenVoiceRoom={handleOpenVoiceRoom} />
        ) : user.role === 'ADMIN' ? (
          <AssignerDashboard onOpenVoiceRoom={handleOpenVoiceRoom} />
        ) : (
          <AssignerDashboard onOpenVoiceRoom={handleOpenVoiceRoom} />
        )}
      </main>

      {/* Global Interactive Web Audio Voice Room Modal */}
      <AudioVoiceRoom
        isOpen={voiceRoomOpen}
        onClose={() => setVoiceRoomOpen(false)}
        taskTitle={voiceRoomTitle}
        taskId={voiceRoomTaskId}
      />
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  );
}
