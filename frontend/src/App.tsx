import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { LoginView } from './views/LoginView';
import { DedicatedDashboard } from './views/DedicatedDashboard';
import { AssignerDashboard } from './views/AssignerDashboard';
import { InternDashboard } from './views/InternDashboard';
import { AdminDashboard } from './views/AdminDashboard';

const MainLayout: React.FC = () => {
  const { user, isLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<'dashboard' | 'workspace' | 'system'>('dashboard');
  const [targetTaskId, setTargetTaskId] = useState<string | undefined>(undefined);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        <div className="flex flex-col items-center space-y-3">
          <div className="w-9 h-9 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-sm font-medium tracking-wide">Connecting to local workspace...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <LoginView />;
  }

  const handleNavigateToWorkspace = (taskId?: string) => {
    if (taskId) setTargetTaskId(taskId);
    setActiveTab('workspace');
  };

  return (
    <div className="min-h-screen text-slate-100 flex flex-col">
      <Navbar
        activeTab={activeTab}
        setActiveTab={(tab: string) => setActiveTab(tab as any)}
      />

      <main className="flex-1">
        {user.role === 'INTERN' ? (
          <InternDashboard initialTaskId={targetTaskId} />
        ) : activeTab === 'dashboard' ? (
          <DedicatedDashboard onNavigateToWorkspace={handleNavigateToWorkspace} />
        ) : activeTab === 'system' && user.role === 'ADMIN' ? (
          <AdminDashboard />
        ) : (
          <AssignerDashboard initialTaskId={targetTaskId} />
        )}
      </main>
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
