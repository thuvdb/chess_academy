import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Classes from './pages/Classes';
import StudentList from './pages/StudentList';
import Schedule from './pages/Schedule';
import Scanner from './pages/Scanner';
import Puzzles from './pages/Puzzles';
import Practice from './pages/Practice';
import Assignments from './pages/Assignments';
import Leaderboard from './pages/Leaderboard';
import PrivateRoute from './components/PrivateRoute';
import AppLayout from './components/AppLayout';

function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
            border: '1px solid #334155',
          },
        }}
      />
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected Routes — wrapped in AppLayout (sidebar) */}
        <Route element={<PrivateRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/classes" element={<Classes />} />
            <Route path="/classes/:classId" element={<StudentList />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/scanner" element={<Scanner />} />
            <Route path="/puzzles" element={<Puzzles />} />
            <Route path="/practice" element={<Practice />} />
            <Route path="/assignments" element={<Assignments />} />
            <Route path="/leaderboard" element={<Leaderboard />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
