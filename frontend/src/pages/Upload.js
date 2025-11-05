import React, {useState} from 'react';
import axios from 'axios';
export default function Upload(){
  const [file,setFile]=useState(null);
  const [msg,setMsg]=useState('');
  const upload = async ()=>{
    if(!file) return setMsg('Select file');
    const fd = new FormData(); fd.append('file', file);
    const token = localStorage.getItem('token');
    try{
      const res = await axios.post('/api/upload', fd, { headers: { Authorization: 'Bearer '+ token }});
      setMsg('Uploaded: '+ res.data.document_id);
    }catch(e){
      setMsg('Upload failed');
    }
  };
  return (
    <div className="max-w-lg mx-auto bg-white p-6 rounded shadow">
      <h2 className="text-xl font-bold mb-4">Upload Event Document</h2>
      <input type="file" onChange={e=>setFile(e.target.files[0])} className="mb-4" />
      <button className="bg-green-600 text-white px-4 py-2 rounded" onClick={upload}>Upload</button>
      <p className="mt-3">{msg}</p>
    </div>
  );
}
