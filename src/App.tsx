
import { AuthProvider } from './hooks/useAuth';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import AuthPage from './pages/auth/AuthPage';
import Home from './pages/Home';
import { Toaster } from "@/components/ui/toaster";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Home />,
  },
  {
    path: "/auth",
    element: <AuthPage />,
  },
]);

function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
      <Toaster />
    </AuthProvider>
  );
}

export default App;
