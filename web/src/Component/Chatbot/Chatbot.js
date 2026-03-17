import React, { useState, useRef, useEffect } from 'react';
import './Chatbot.scss';

function Chatbot() {
  const [messages, setMessages] = useState([
    { role: 'bot', content: 'Xin chào! Tôi là AI giám sát an ninh. Bạn cần kiểm tra dữ liệu camera lúc nào?' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatContainerRef = useRef(null);

  // Tự động cuộn xuống khi có tin nhắn mới
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const startStreaming = async () => {
    if (!input.trim() || isTyping) return;

    const userQuestion = input;
    setMessages(prev => [...prev, { role: 'user', content: userQuestion }]);
    setInput('');
    setIsTyping(true);

    // Thêm một tin nhắn trống cho Bot để chuẩn bị hứng dữ liệu stream
    setMessages(prev => [...prev, { role: 'bot', content: '' }]);

    try {
      const response = await fetch('http://localhost:8000/ask', { // Địa chỉ FastAPI của bạn
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userQuestion })
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        
        // Cập nhật từng chữ vào tin nhắn cuối cùng của Bot
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMsg = newMessages[newMessages.length - 1];
          lastMsg.content += chunk;
          return newMessages;
        });
      }
    } catch (error) {
      setMessages(prev => [...prev, { role: 'bot', content: 'Lỗi kết nối Server.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="chatbot-wrapper">
      <div className="header-logo">
        <div className="logo-box">AI</div>
      </div>

      <h2>ELEVATOR CHATBOT</h2>

      <div id="chat-container" ref={chatContainerRef}>
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role === 'user' ? 'user-message' : 'ai-message'}`}>
            {msg.content === '' && msg.role === 'bot' ? <em>Đang trích xuất dữ liệu...</em> : msg.content}
          </div>
        ))}
      </div>

      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Hỏi về sự cố, người ngã, nằm..."
          onKeyPress={(e) => e.key === 'Enter' && startStreaming()}
          disabled={isTyping}
        />
        <button onClick={startStreaming} disabled={isTyping}>
          {isTyping ? '...' : 'Gửi'}
        </button>
      </div>
    </div>
  );
}

export default Chatbot;