import React, { useState, useContext } from "react";
import axios from "axios";
import { AuthContext } from "../context/AuthContext";

export default function Upload() {
  const { token, user } = useContext(AuthContext);
  const [file, setFile] = useState(null);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const upload = async () => {
    if (!file) return setMsg("Please select a file first.");
    const fd = new FormData();
    fd.append("file", file);

    try {
      setLoading(true);
      const res = await axios.post("http://localhost:5000/api/upload", fd, {
        headers: {
          Authorization: "Bearer " + token,
          "Content-Type": "multipart/form-data",
        },
      });
      setMsg(`✅ Uploaded successfully (Document ID: ${res.data.document_id})`);
    } catch (e) {
      setMsg(
        `❌ Upload failed: ${
          e.response?.data?.message || e.message || "Server Error"
        }`
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-lg mx-auto bg-white p-6 rounded shadow">
      <h2 className="text-xl font-bold mb-4">Upload Event Document</h2>
      <p className="mb-2 text-sm text-gray-600">
        Logged in as: {user?.username} ({user?.role})
      </p>

      <input
        type="file"
        onChange={(e) => setFile(e.target.files[0])}
        className="mb-4"
      />
      <button
        onClick={upload}
        disabled={loading}
        className="bg-green-600 text-white px-4 py-2 rounded disabled:opacity-70"
      >
        {loading ? "Uploading..." : "Upload"}
      </button>
      <p className="mt-3 text-sm text-gray-700">{msg}</p>
    </div>
  );
}
