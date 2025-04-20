
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/useAuth';

export default function Home() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

  const handleAuthClick = () => {
    if (user) {
      signOut();
    } else {
      navigate('/auth');
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4">
      <h1 className="mb-8 text-3xl font-bold">F1 Live Timing Dashboard</h1>
      
      <div className="w-full max-w-md">
        {user ? (
          <div className="rounded-lg border p-4 shadow-sm">
            <p className="mb-2 text-lg">Welcome, {user.email}</p>
            <Button className="w-full" onClick={handleAuthClick}>
              Sign Out
            </Button>
          </div>
        ) : (
          <div className="rounded-lg border p-4 shadow-sm">
            <p className="mb-2 text-lg">Please sign in to access all features</p>
            <Button className="w-full" onClick={handleAuthClick}>
              Sign In / Register
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
