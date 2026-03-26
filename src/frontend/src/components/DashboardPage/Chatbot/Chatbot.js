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
    // 1. Chặn đứng việc gửi trùng lặp (Fix lỗi StrictMode và spam click)
    if (!input.trim() || isTyping) return;

    const userQuestion = input;
    setInput('');
    setIsTyping(true);

    // 2. Thêm cả 2 tin nhắn cùng lúc để đảm bảo tính đồng bộ
    setMessages(prev => [
      ...prev, 
      { role: 'user', content: userQuestion },
      { role: 'bot', content: '' } // Tin nhắn trống để chuẩn bị hứng stream
    ]);

    try {
        const response = await fetch('http://localhost:5000/ask', {
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

            // 3. Cập nhật nội dung cho tin nhắn cuối cùng (là tin nhắn Bot)
            setMessages(prev => {
                const newMessages = [...prev];
                const lastIdx = newMessages.length - 1;
                newMessages[lastIdx] = { 
                    ...newMessages[lastIdx], 
                    content: newMessages[lastIdx].content + chunk 
                };
                return newMessages;
            });
        }
    } catch (error) {
        console.error("Streaming error:", error);
        // Cập nhật thông báo lỗi vào đúng tin nhắn Bot cuối cùng
        setMessages(prev => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1].content = 'Lỗi kết nối Server.';
            return newMessages;
        });
    } finally {
        setIsTyping(false);
    }
  };

  return (
    <div className="chatbot-main-container"> 
      <div className="chatbot-wrapper">
        
        {/* Tiêu đề */}
        <div className="chatbot-header-bg">
          <h2>ELEVATOR CHATBOT</h2>
        </div>

        {/* Vùng tin nhắn */}
        <div id="chat-container" ref={chatContainerRef}>
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role === 'user' ? 'user-message' : 'ai-message'}`}>
              {msg.content === '' && msg.role === 'bot' ? <em>Đang trích xuất dữ liệu...</em> : msg.content}
            </div>
          ))}
        </div>

        {/* Vùng nhập liệu */}
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
    </div>
  );
}

export default Chatbot;