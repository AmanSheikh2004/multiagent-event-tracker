// src/components/Sidebar.js
import React, { useContext } from "react";
import { Link, useLocation } from "react-router-dom";
import { AuthContext } from "../context/AuthContext";
import { Home, Upload, ClipboardCheck, FileText, BarChart3 } from "lucide-react";

const Sidebar = () => {
  const { user } = useContext(AuthContext);
  const location = useLocation();

  if (!user) return null;

  const linksByRole = {
    student: [
      { path: "/upload", name: "Upload", icon: <Upload size={18} /> },
      { path: "/tracker", name: "Tracker", icon: <BarChart3 size={18} /> },
    ],
    teacher: [
      { path: "/validate", name: "Validate", icon: <ClipboardCheck size={18} /> },
      { path: "/tracker", name: "Tracker", icon: <BarChart3 size={18} /> },
    ],
    iqc: [
      { path: "/validate", name: "Validate", icon: <ClipboardCheck size={18} /> },
      { path: "/admin", name: "Admin", icon: <FileText size={18} /> },
      { path: "/tracker", name: "Tracker", icon: <BarChart3 size={18} /> },
    ],
  };

  const links = linksByRole[user.role] || [];

  return (
    <aside className="w-60 bg-gray-900 text-white flex flex-col p-4">
      <h2 className="text-xl font-semibold mb-8 tracking-wide flex items-center gap-2">
        <Home size={20} /> Tracker
      </h2>

      <nav className="flex flex-col space-y-3">
        {links.map((link) => (
          <Link
            key={link.path}
            to={link.path}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              location.pathname === link.path
                ? "bg-indigo-600 text-white"
                : "hover:bg-gray-700 text-gray-300"
            }`}
          >
            {link.icon}
            {link.name}
          </Link>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;
