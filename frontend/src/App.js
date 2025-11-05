import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Login from './pages/Login';
import Upload from './pages/Upload';
import Tracker from './pages/Tracker';
import Validate from './pages/Validate';
import Admin from './pages/Admin';

export default function App(){
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow p-4">
          <div className="container mx-auto flex justify-between">
            <div><Link to="/" className="font-bold">MultiAgent Tracker</Link></div>
            <div className="space-x-4">
              <Link to="/upload">Upload</Link>
              <Link to="/tracker">Tracker</Link>
              <Link to="/admin">Admin</Link>
            </div>
          </div>
        </nav>
        <div className="container mx-auto p-6">
          <Routes>
            <Route path="/" element={<Login/>} />
            <Route path="/upload" element={<Upload/>} />
            <Route path="/tracker" element={<Tracker/>} />
            <Route path="/validate" element={<Validate/>} />
            <Route path="/admin" element={<Admin/>} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
