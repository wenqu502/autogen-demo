import React from 'react';

const Home = () => {
  return (
    <div className="card">
      <h1>欢迎使用 AutoGen 多智能体协作平台</h1>
      <p>这是一个基于 AutoGen 和 DeepSeek 的本地化多智能体协作环境。</p>
      <h3>功能介绍：</h3>
      <ul>
        <li><strong>智能体设置</strong>：创建和配置不同的 AI 智能体，定义它们的角色和能力。</li>
        <li><strong>对话界面</strong>：发起多智能体群聊，观察它们如何协作解决问题。</li>
      </ul>
      <p>请从左侧菜单开始探索。</p>
    </div>
  );
};

export default Home;
