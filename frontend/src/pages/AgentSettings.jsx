import React, { useState, useEffect } from 'react';
import axios from 'axios';

const AgentSettings = () => {
  const [agents, setAgents] = useState([]);
  const [formData, setFormData] = useState({
    name: '',
    system_message: '',
  });

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await axios.get('/api/agents');
      setAgents(response.data);
    } catch (error) {
      console.error('Error fetching agents:', error);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/agents', formData);
      setFormData({ name: '', system_message: '' });
      fetchAgents();
    } catch (error) {
      console.error('Error creating agent:', error);
      alert('Failed to create agent');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure?')) return;
    try {
      await axios.delete(`/api/agents/${id}`);
      fetchAgents();
    } catch (error) {
      console.error('Error deleting agent:', error);
    }
  };

  return (
    <div>
      <div className="card">
        <h2>创建新智能体</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>名称 (Name)</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g. Coder, ProductManager"
              required
            />
          </div>
          <div className="form-group">
            <label>系统提示词 (System Message)</label>
            <textarea
              name="system_message"
              value={formData.system_message}
              onChange={handleChange}
              rows="4"
              placeholder="定义智能体的角色和行为..."
              required
            />
          </div>
          <button type="submit" className="btn">创建智能体</button>
        </form>
      </div>

      <div className="card">
        <h2>已有智能体列表</h2>
        {agents.length === 0 ? (
          <p>暂无智能体，请先创建。</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid #ddd' }}>
                <th style={{ padding: '10px' }}>名称</th>
                <th style={{ padding: '10px' }}>系统提示词</th>
                <th style={{ padding: '10px' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '10px', fontWeight: 'bold' }}>{agent.name}</td>
                  <td style={{ padding: '10px', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {agent.system_message}
                  </td>
                  <td style={{ padding: '10px' }}>
                    <button 
                      className="btn btn-danger" 
                      onClick={() => handleDelete(agent.id)}
                      style={{ fontSize: '0.8em', padding: '5px 10px' }}
                    >
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default AgentSettings;
