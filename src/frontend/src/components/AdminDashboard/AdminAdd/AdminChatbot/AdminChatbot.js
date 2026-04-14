import React, { useState, useRef, useEffect } from 'react';
import './AdminChatbot.scss'; 
import { Send, Bot, User, Sparkles } from 'lucide-react';

function AdminChatbot({ mode }) {
  const [messages, setMessages] = useState([
    { 
      role: 'bot', 
      content: mode === 'analytics' 
        ? 'Hệ thống AI Analytics sẵn sàng. Bạn cần trích xuất dữ liệu vận hành Robot không?' 
        : 'Trợ lý AMR đang trực tuyến. Tôi có thể hỗ trợ giám sát và điều phối Real-time.' 
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const startStreaming = async () => {
    if (!input.trim() || isTyping) return;
    
    const userQuestion = input;
    setInput('');
    setIsTyping(true);

    // 1. Thêm tin nhắn User và tạo sẵn 1 tin nhắn Bot trống
    setMessages(prev => [
      ...prev, 
      { role: 'user', content: userQuestion }, 
      { role: 'bot', content: '' }
    ]);

    try {
        const response = await fetch('http://localhost:5000/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: userQuestion })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        // Biến tạm để giữ toàn bộ nội dung đã nhận được từ Stream
        let accumulatedContent = ""; 

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, { stream: true });
            accumulatedContent += chunk; // Cộng dồn vào biến tạm

            // 2. CẬP NHẬT STATE KHÔNG GÂY NHÂN ĐÔI CHỮ
            setMessages(prev => {
                const newMessages = [...prev];
                const lastIdx = newMessages.length - 1;
                
                // Chỉ cập nhật nếu tin nhắn cuối cùng đúng là của bot
                if (newMessages[lastIdx].role === 'bot') {
                    newMessages[lastIdx] = { 
                      ...newMessages[lastIdx], 
                      content: accumulatedContent // Gán bằng nội dung đã cộng dồn
                    };
                }
                return newMessages;
            });
        }
    } catch (error) {
        console.error("Streaming error:", error);
        setMessages(prev => {
            const newMsgs = [...prev];
            newMsgs[newMsgs.length - 1].content = 'Lỗi kết nối Server AI.';
            return newMsgs;
        });
    } finally {
        setIsTyping(false);
    }
  };

  return (
    <div className="admin-chatbot-v3"> 
      <div className="glass-header">
         <div className="ai-brand">
            <div className="logo-glow"><Bot size={22} /></div>
            <div className="text-group">
              <span className="main-title">AI ELEVATOR</span>
              <span className="sub-title">{mode === 'analytics' ? 'Data Analysis Mode' : 'Real-time Control'}</span>
            </div>
         </div>
         <div className="pulse-status">
            <div className="pulse-dot"></div> Active
         </div>
      </div>

      <div className="message-container" ref={chatContainerRef}>
        {messages.map((msg, index) => (
          <div key={index} className={`chat-row ${msg.role}`}>
            <div className="icon-wrapper">
              {msg.role === 'bot' ? <Sparkles size={16} /> : <User size={16} />}
            </div>
            <div className="content-wrapper">
              <div className="bubble-chat">
                {msg.role === 'bot' && msg.content === '' ? (
                  <div className="typing-indicator"><span></span><span></span><span></span></div>
                ) : (
                  // whiteSpace pre-wrap giúp AI xuống dòng chuẩn xác
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bottom-bar">
        <div className="input-box-modern">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Gửi yêu cầu cho AI trợ lý..."
            onKeyDown={(e) => e.key === 'Enter' && startStreaming()}
            disabled={isTyping}
          />
          <button onClick={startStreaming} disabled={isTyping} className="send-btn-v3">
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default AdminChatbot;