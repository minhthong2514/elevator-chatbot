require('dotenv').config(); // Dòng này bắt buộc ở trên cùng
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const axios = require('axios');
const app = express();
app.use(express.json());
app.use(cors());

// Lấy dữ liệu từ .env
const PORT = process.env.PORT;
const MONGO_URI = process.env.MONGODB_URI;
const CAMERA_URL = process.env.FASTAPI_URL;

// Kết nối MongoDB bằng biến môi trường
mongoose.connect(MONGO_URI)
    .then(() => console.log("Đã kết nối MongoDB thành công"))
    .catch(err => console.error("Lỗi kết nối MongoDB:", err));

// Định nghĩa Schema (Giữ nguyên cấu trúc của Tài)
const UserSchema = new mongoose.Schema({
    username: { type: String, required: true, unique: true },
    password: { type: String, required: true },
    rank: { type: String, default: 'user' }
}, { versionKey: false });

const User = mongoose.model('User', UserSchema, 'Human_Resource_Management');

// API ĐĂNG KÝ
app.post('/api/register', async (req, res) => {
    try {
        const { username, password } = req.body;
        const cleanUsername = username.trim();

        const userExists = await User.findOne({ username: cleanUsername });
        if (userExists) {
            return res.status(400).json({ success: false, message: "Tên đăng nhập đã tồn tại!" });
        }

        const newUser = new User({ username: cleanUsername, password, rank: "user" });
        await newUser.save();
        res.json({ success: true, message: "Đăng ký thành công!" });
    } catch (err) {
        res.status(500).json({ success: false, message: "Lỗi hệ thống!" });
    }
});

// API ĐĂNG NHẬP
app.post('/api/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        const user = await User.findOne({ username: username.trim(), password });

        if (user) {
            console.log(`👤 User ${username} login thành công`);
            res.json({ 
                success: true, 
                rank: user.rank, 
                cameraUrl: CAMERA_URL, // Lấy từ .env
                message: `Chào mừng ${username}!` 
            });
        } else {
            res.status(401).json({ success: false, message: "Sai tài khoản hoặc mật khẩu!" });
        }
    } catch (err) {
        console.error(err);
        res.status(500).json({ success: false, message: "Lỗi Server!" });
    }
});

app.post('/ask', async (req, res) => {
    const { question } = req.body;

    // Thiết lập Header để chuẩn bị Stream về cho React
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.setHeader('Transfer-Encoding', 'chunked'); // Đảm bảo stream mượt mà

    try {
        // Node.js "Call API" sang Python AI Service
        const aiResponse = await axios({
            method: 'post',
            url: 'http://localhost:8081/ask', // Cổng của Python FastAPI
            data: { question: question },
            responseType: 'stream' // Yêu cầu nhận dữ liệu dạng dòng chảy
        });

        // Chuyển tiếp dòng chảy dữ liệu từ Python sang React
        aiResponse.data.on('data', (chunk) => {
            res.write(chunk); 
        });

        aiResponse.data.on('end', () => {
            res.end();
        });

        aiResponse.data.on('error', (err) => {
            console.error("Stream error:", err);
            res.end();
        });

    } catch (error) {
        console.error("Lỗi gọi AI Service:", error.message);
        res.write("Lỗi: Không thể kết nối với AI Service.");
        res.end();
    }
});

app.listen(PORT, () => console.log(`Server Backend chạy tại: http://localhost:${PORT}`));