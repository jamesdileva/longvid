import { NavLink, Route, Routes } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import Settings from './pages/Settings';

export default function App() {
  return (
    <div className="app-shell">
      <nav className="sidebar">
        <div className="brand">LongVid</div>
        <NavLink to="/" end>
          Dashboard
        </NavLink>
        <NavLink to="/projects">Projects</NavLink>
        <NavLink to="/settings">Settings</NavLink>
      </nav>
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects" element={<Projects />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
