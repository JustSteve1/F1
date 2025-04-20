
import { useNavigate } from 'react-router-dom';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from '@/hooks/useAuth';
import { Toaster } from "@/components/ui/toaster";
import { useF1Sessions, useCurrentF1Session } from '@/hooks/useF1Sessions';

export default function Home() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const { data: sessions, isLoading: isLoadingSessions } = useF1Sessions();
  const { data: currentSession } = useCurrentF1Session();

  // Redirect to auth page if user is not logged in
  const handleAuthClick = () => {
    if (!user) {
      navigate('/auth');
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center">F1 Live Timing</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {user ? (
            <div className="space-y-4">
              <p className="text-center">Welcome, {user.email}!</p>
              
              {currentSession && (
                <Card className="bg-red-50 border-red-200">
                  <CardHeader className="py-2">
                    <CardTitle className="text-sm text-red-600">LIVE NOW</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="font-bold">{currentSession.name}</p>
                    <p className="text-sm text-gray-600">{currentSession.circuit}</p>
                  </CardContent>
                </Card>
              )}

              {isLoadingSessions ? (
                <p className="text-center text-gray-500">Loading sessions...</p>
              ) : sessions?.length ? (
                <div className="space-y-2">
                  <h3 className="font-semibold">Recent Sessions</h3>
                  {sessions.map((session) => (
                    <Card key={session.id} className="cursor-pointer hover:bg-gray-50" onClick={() => navigate(`/session/${session.id}`)}>
                      <CardContent className="p-4">
                        <p className="font-medium">{session.name}</p>
                        <p className="text-sm text-gray-600">{session.circuit}</p>
                        <p className="text-xs text-gray-500">{new Date(session.start_time).toLocaleDateString()}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <p className="text-center text-gray-500">No sessions available</p>
              )}

              <Button 
                onClick={signOut} 
                variant="outline" 
                className="w-full"
              >
                Sign Out
              </Button>
            </div>
          ) : (
            <Button 
              onClick={handleAuthClick} 
              className="w-full"
            >
              Sign In / Sign Up
            </Button>
          )}
        </CardContent>
      </Card>
      <Toaster />
    </div>
  );
}
