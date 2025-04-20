
import { AuthProvider } from './hooks/useAuth';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import AuthPage from './pages/auth/AuthPage';
import Home from './pages/Home';

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
    </AuthProvider>
  );
}

export default App;
