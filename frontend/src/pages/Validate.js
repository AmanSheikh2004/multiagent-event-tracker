import React, { useEffect, useState } from "react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const DEPARTMENTS = [
  { value: "AIML", label: "Artificial Intelligence & Machine Learning" },
  { value: "CSE(Core)", label: "Computer Science & Engineering (Core)" },
  { value: "ISE", label: "Information Science & Engineering" },
  { value: "ECE", label: "Electronics & Communication Engineering" },
  { value: "AERO", label: "Aeronautical Engineering" },
];

const EVENT_TYPES = [
  { value: "Seminar", label: "Seminar" },
  { value: "Workshop", label: "Workshop" },
  { value: "Competitions", label: "Competitions" },
  { value: "General Event", label: "General Event" },
];


function DocumentModal({ open, onClose, docId, token, onValidated }) {
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [category, setCategory] = useState("");
  const [department, setDepartment] = useState("");

  useEffect(() => {
    if (!open || !docId) return;
    setLoading(true);
    (async () => {
      try {
        const res = await axios.get(`http://localhost:5000/api/document/${docId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setDoc(res.data);
        if (res.data.events && res.data.events.length > 0) {
          const ev = res.data.events[0];
          setName(ev.name || "");
          setDate(ev.date || "");
          setCategory(ev.category || "");
          setDepartment(ev.department || "");
        }
      } catch (err) {
        console.error("Failed to load document", err);
      } finally {
        setLoading(false);
      }
    })();
  }, [open, docId, token]);

  if (!open) return null;

  const handleValidate = async () => {
    try {
      const evId = doc.events[0].id;
      await axios.post(
        `http://localhost:5000/api/validate/${evId}`,
        { name, date, category, department },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      onValidated(evId);
      onClose();
      alert("✅ Event validated!");
    } catch (e) {
      console.error("Validation failed", e);
      alert("Validation failed!");
    }
  };

  const fileUrl = `http://localhost:5000/api/document/${docId}/file?token=${token}`;


  return (
    <div className="fixed inset-0 flex items-start justify-center p-6 z-50">
      <div className="absolute inset-0 bg-black opacity-40" onClick={onClose}></div>
      <div className="bg-white rounded-lg p-6 shadow-xl relative z-50 w-full max-w-3xl max-h-[85vh] overflow-auto">
        <h2 className="text-xl font-bold mb-3">Document Review</h2>
        <a href={fileUrl} target="_blank" rel="noreferrer" className="text-blue-600 underline">
          📄 Open Uploaded File
        </a>
        <div className="mt-4 space-y-2">
          <label className="block">
            <span className="text-sm font-medium">Event Name:</span>
            <input value={name} onChange={(e) => setName(e.target.value)} className="border p-2 w-full rounded" />
          </label>
          {/* Date Picker */}
        <label className="block">
          <span className="text-sm font-medium">Date:</span>
          <input
            type="date"
            value={date ? date.slice(0, 10) : ""}
            onChange={(e) => setDate(e.target.value)}
            className="border p-2 w-full rounded"
          />
        </label>
        {/* Event Type Dropdown */}
        <label className="block">
          <span className="text-sm font-medium">Event Type:</span>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="border p-2 w-full rounded"
          >
            <option value="">-- Select Event Type --</option>
            {EVENT_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </label>
        {/* Department Dropdown */}
        <label className="block">
          <span className="text-sm font-medium">Department:</span>
          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="border p-2 w-full rounded"
          >
            <option value="">-- Select Department --</option>
            {DEPARTMENTS.map((dept) => (
              <option key={dept.value} value={dept.value}>
                {dept.label}
              </option>
            ))}
          </select>
        </label>
        </div>

        <div className="mt-4">
          <h3 className="font-semibold">Extracted Text</h3>
          <pre className="bg-gray-50 border p-3 rounded text-sm overflow-auto max-h-40">
            {doc?.document?.raw_text || "No extracted text available."}
          </pre>
        </div>

        <div className="mt-4">
          <h3 className="font-semibold">Entities</h3>
          <ul className="list-disc pl-5">
            {doc?.entities?.length ? (
              doc.entities.map((e, i) => (
                <li key={i}>
                  <strong>{e.label}</strong>: {e.text} (conf: {e.confidence})
                </li>
              ))
            ) : (
              <li>No entities found.</li>
            )}
          </ul>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={handleValidate} className="bg-green-600 text-white px-4 py-2 rounded">
            Validate & Save
          </button>
          <button onClick={onClose} className="bg-gray-300 px-4 py-2 rounded">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Validate() {
  const { token } = useAuth();
  const [events, setEvents] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState(null);

  useEffect(() => {
    fetchEvents();
  }, [token]);

  const fetchEvents = async () => {
    try {
      const res = await axios.get("http://localhost:5000/api/validate/events", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setEvents(res.data.events || []);
    } catch (err) {
      console.error("Error fetching events", err);
    }
  };

  const onValidated = (id) => {
    setEvents(events.filter((e) => e.id !== id));
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-2xl font-bold mb-4">Validation Queue</h1>
      {events.length === 0 ? (
        <p>No pending events 🎉</p>
      ) : (
        <table className="w-full border bg-white rounded shadow">
          <thead>
            <tr className="bg-gray-200">
              <th className="p-2 border">Event Name</th>
              <th className="p-2 border">Date</th>
              <th className="p-2 border">Category</th>
              <th className="p-2 border">Department</th>
              <th className="p-2 border">Uploaded By</th>
              <th className="p-2 border">Action</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id} className="border-t hover:bg-gray-100">
                <td className="p-2 border">{e.name || "Unknown"}</td>
                <td className="p-2 border">{e.date || "N/A"}</td>
                <td className="p-2 border">{e.category || "General"}</td>
                <td className="p-2 border">{e.department || "Unknown"}</td>
                <td className="p-2 border">{e.uploaded_by}</td>
                <td className="p-2 border text-center">
                  <button
                    onClick={() => {
                      setSelectedDocId(e.document_id);
                      setModalOpen(true);
                    }}
                    className="bg-blue-600 text-white px-3 py-1 rounded mr-2"
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <DocumentModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        docId={selectedDocId}
        token={token}
        onValidated={onValidated}
      />
    </div>
  );
}
