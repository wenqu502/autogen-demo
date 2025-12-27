import React, { useState, useEffect } from 'react';
import axios from 'axios';

const Chat = () => {
  const [agents, setAgents] = useState([]);
  const [selectedAgents, setSelectedAgents] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

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

  const handleAgentToggle = (id) => {
    setSelectedAgents(prev => 
      prev.includes(id) ? prev.filter(aid => aid !== id) : [...prev, id]
    );
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || selectedAgents.length === 0) return;

    setLoading(true);
    // 先显示用户的消息
    const userMsg = { role: 'user', content: input, name: 'User' };
    setMessages(prev => [...prev, userMsg]);
    
    try {
      const response = await axios.post('/api/chat', {
        message: input,
        agent_ids: selectedAgents
      });
      
      if (response.data.messages) {
        // 过滤掉第一条用户消息（因为我们已经手动添加了），或者直接使用返回的全量历史
        // AutoGen 返回的是完整对话历史，包含 system prompt 等
        // 我们只展示非 system 的消息
        const newMessages = response.data.messages.filter(m => m.role !== 'system');
        setMessages(newMessages);
      }
      
      setInput('');
    } catch (error) {
      console.error('Error sending message:', error);
      alert('Error during chat: ' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="card">
        <h3>参与对话的智能体</h3>
        {agents.length === 0 ? (
          <p>请先在设置页添加智能体</p>
        ) : (
          <div className="agent-selector">
            {agents.map(agent => (
              <label key={agent.id} className="agent-checkbox">
                <input
                  type="checkbox"
                  checked={selectedAgents.includes(agent.id)}
                  onChange={() => handleAgentToggle(agent.id)}
                />
                {agent.name}
              </label>
            ))}
          </div>
        )}
      </div>

      <div className="messages-area">
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', color: '#9ca3af', marginTop: '50px' }}>
            选择智能体并开始对话...
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role === 'user' ? 'user' : 'agent'}`}>
              <div className="message-header">{msg.name || msg.role}</div>
              <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
            </div>
          ))
        )}
        {loading && <div className="message agent"><em>智能体正在思考和协作...</em></div>}
      </div>

      <div className="input-area">
        <form onSubmit={handleSend} style={{ display: 'flex', gap: '10px' }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入你的任务..."
            rows="3"
            style={{ flex: 1, padding: '10px', borderRadius: '6px', border: '1px solid #d1d5db' }}
            disabled={loading}
          />
          <button 
            type="submit" 
            className="btn" 
            disabled={loading || selectedAgents.length === 0 || !input.trim()}
            style={{ height: 'auto' }}
          >
            发送
          </button>
        </form>
      </div>
    </div>
  );
};

export default Chat;
