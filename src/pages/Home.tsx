
import { useNavigate } from 'react-router-dom';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from '@/hooks/useAuth';
import { Toaster } from "@/components/ui/toaster";

export default function Home() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

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
