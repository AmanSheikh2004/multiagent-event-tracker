import React, {useState, useEffect} from 'react';
import axios from 'axios';
export default function Tracker(){
  const [data,setData]=useState(null);
  useEffect(()=>{ const token=localStorage.getItem('token'); axios.get('/api/tracker',{headers:{Authorization:'Bearer '+token}}).then(r=>setData(r.data)).catch(()=>{});},[]);
  if(!data) return <div>Loading...</div>;
  return (
    <div className="space-y-6">
      {Object.keys(data).map(dept=> (
        <div key={dept} className="bg-white p-4 rounded shadow">
          <h3 className="text-lg font-bold">{dept}</h3>
          <p>Total events: {data[dept].total}</p>
          <div className="grid grid-cols-3 gap-4 mt-3">
            {Object.entries(data[dept].by_category).map(([cat,count])=> (
              <div key={cat} className="p-3 border rounded">
                <div className="text-sm font-semibold">{cat}</div>
                <div className="text-2xl">{count}</div>
              </div>
            ))}
          </div>
          <div className="mt-4">
            <table className="w-full table-auto">
              <thead><tr><th>Name</th><th>Date</th><th>Category</th></tr></thead>
              <tbody>
                {data[dept].events.map((e,i)=> <tr key={i}><td>{e.name}</td><td>{e.date}</td><td>{e.category}</td></tr>)}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
