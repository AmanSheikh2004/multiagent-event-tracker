import React, {useState} from 'react';
import axios from 'axios';
export default function Login(){
  const [username,setUsername]=useState('');
  const [password,setPassword]=useState('');
  const [msg,setMsg]=useState('');
  const login = async ()=>{
    try{
      const res = await axios.post('/api/auth/login',{username,password});
      localStorage.setItem('token', res.data.token);
      setMsg('Logged in');
    }catch(e){
      setMsg('Login failed');
    }
  };
  return (
    <div className="max-w-md mx-auto bg-white p-6 rounded shadow">
      <h2 className="text-xl font-bold mb-4">Login</h2>
      <input className="w-full p-2 border mb-3" placeholder="username" value={username} onChange={e=>setUsername(e.target.value)} />
      <input type="password" className="w-full p-2 border mb-3" placeholder="password" value={password} onChange={e=>setPassword(e.target.value)} />
      <button className="bg-blue-600 text-white px-4 py-2 rounded" onClick={login}>Login</button>
      <p className="mt-3">{msg}</p>
    </div>
  );
}
