import React, { useEffect, useState, useContext } from "react";
import axios from "axios";
import { AuthContext } from "../context/AuthContext";

export default function Tracker() {
  const { token } = useContext(AuthContext);
  const [documents, setDocuments] = useState([]);

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const res = await axios.get("http://localhost:5000/api/documents", {
          headers: { Authorization: "Bearer " + token },
        });
        setDocuments(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchDocs();
  }, [token]);

  return (
    <div className="max-w-4xl mx-auto bg-white p-6 rounded shadow">
      <h2 className="text-xl font-bold mb-4">My Uploaded Documents</h2>
      <table className="min-w-full border text-sm">
        <thead className="bg-gray-100">
          <tr>
            <th className="border px-3 py-2">File Name</th>
            <th className="border px-3 py-2">Status</th>
            <th className="border px-3 py-2">Uploaded At</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((d) => (
            <tr key={d.id}>
              <td className="border px-3 py-2">{d.filename}</td>
              <td className="border px-3 py-2">{d.status}</td>
              <td className="border px-3 py-2">
                {new Date(d.uploaded_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
