require('dotenv').config(); 
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const axios = require('axios');

const app = express();
app.use(express.json());
app.use(cors());

// --- 1. LẤY CẤU HÌNH TỪ .ENV ---
const PORT = process.env.PORT || 5000;
const MONGO_URI = process.env.MONGODB_URI;
const CAMERA_URL = process.env.FASTAPI_URL;

// --- 2. KẾT NỐI MONGODB ---
mongoose.connect(MONGO_URI)
    .then(() => console.log("Da ket noi MongoDB thanh cong"))
    .catch(err => console.error("Loi ket noi MongoDB:", err));

// --- 3. ĐỊNH NGHĨA SCHEMA & MODEL ---
// Cập nhật Schema mới để lưu đầy đủ thông tin cá nhân như Tài yêu cầu
const UserSchema = new mongoose.Schema({
    email: { type: String, required: true, unique: true },     // Địa chỉ Gmail
    fullName: { type: String, required: true },                // Tên của bạn
    dob: { type: String, required: true },                     // Ngày tháng năm sinh (Dạng DD/MM/YYYY)
    role: { type: String, required: true },                    // Chức danh (admin/user)
    username: { type: String, required: true, unique: true },  // Tên đăng nhập
    password: { type: String, required: true },                // Mật khẩu
    rank: { type: String, default: 'user' }                    // Phân quyền hệ thống
}, { versionKey: false, timestamps: true });

const User = mongoose.model('User', UserSchema, 'Human_Resource_Management');

// --- 4. CÁC API HỆ THỐNG ---

// API ĐĂNG KÝ (Admin tạo tài khoản mới)
app.post('/api/register', async (req, res) => {
    try {
        const { email, fullName, dob, role, username, password } = req.body;
        const cleanUsername = username.trim();

        // Kiểm tra xem Username hoặc Email đã tồn tại chưa
        const userExists = await User.findOne({ 
            $or: [{ username: cleanUsername }, { email: email }] 
        });

        if (userExists) {
            return res.status(400).json({ 
                success: false, 
                message: "Tên đăng nhập hoặc Email đã tồn tại!" 
            });
        }

        // Tạo dữ liệu mới theo định dạng 7 mục của Tài
        const newUser = new User({ 
            email,
            fullName,
            dob,
            role,
            username: cleanUsername, 
            password, 
            rank: role // Đồng bộ rank với chức danh đã chọn trong form
        });

        await newUser.save();
        res.json({ success: true, message: "Tạo tài khoản thành công!" });
    } catch (err) {
        console.error("Loi Register:", err);
        res.status(500).json({ success: false, message: "Lỗi hệ thống khi lưu MongoDB!" });
    }
});

// API CẬP NHẬT THÔNG TIN (Chỉ sửa Email, Password, Rank dựa trên Username)
app.put('/api/update-user', async (req, res) => {
    try {
        const { username, email, password, rank } = req.body;

        if (!username) {
            return res.status(400).json({ success: false, message: "Thiếu tên đăng nhập!" });
        }

        // Tìm và cập nhật: Chỉ lấy các trường được phép sửa
        const updatedUser = await User.findOneAndUpdate(
            { username: username.trim() }, 
            { 
                $set: { 
                    email: email,
                    password: password,
                    rank: rank
                } 
            },
            { new: true, runValidators: true } // Trả về bản ghi mới nhất
        ).select('-_id'); // Ẩn ID cho sạch

        if (!updatedUser) {
            return res.status(404).json({ success: false, message: "Không tìm thấy người dùng!" });
        }

        console.log(`[UPDATE] Tai khoan ${username} da duoc cap nhat`);
        res.json({ 
            success: true, 
            message: "Cập nhật thành công!",
            data: updatedUser 
        });
    } catch (err) {
        console.error("Loi Update:", err);
        res.status(500).json({ success: false, message: "Lỗi hệ thống khi cập nhật!" });
    }
});

// API XÓA NGƯỜI DÙNG (Dựa trên Username)
app.delete('/api/delete-user/:username', async (req, res) => {
    try {
        const { username } = req.params;

        // Không cho phép xóa chính tài khoản Admin đang điều hành (tùy chọn bảo mật)
        if (username.toLowerCase() === 'tai') {
            return res.status(403).json({ success: false, message: "Không thể xóa tài khoản Admin gốc!" });
        }

        const deletedUser = await User.findOneAndDelete({ username: username.trim() });

        if (!deletedUser) {
            return res.status(404).json({ success: false, message: "Không tìm thấy người dùng để xóa!" });
        }

        console.log(`[DELETE] Tai khoan ${username} da bi xoa khỏi hệ thống`);
        res.json({ success: true, message: `Đã xóa thành công người dùng: ${username}` });
    } catch (err) {
        console.error("Loi Delete:", err);
        res.status(500).json({ success: false, message: "Lỗi hệ thống khi xóa dữ liệu!" });
    }
});

// API ĐĂNG NHẬP
app.post('/api/login', async (req, res) => {
    try {
        const { username, password } = req.body;
        // Tìm user khớp tài khoản và mật khẩu
        const user = await User.findOne({ username: username.trim(), password });

        if (user) {
            console.log(`[${user.role.toUpperCase()}] ${user.fullName} đăng nhập thành công`);
            const displayRole = user.role ? user.role.toUpperCase() : 'USER';
            res.json({ 
                success: true, 
                username: user.username,
                fullName: user.fullName, // Trả thêm tên đầy đủ về cho Frontend
                rank: user.role,         // Trả rank (admin/user) để App.js điều hướng
                cameraUrl: CAMERA_URL,    
                message: `Chào mừng ${user.username}!` 
            });
        } else {
            res.status(401).json({ success: false, message: "Sai tài khoản hoặc mật khẩu!" });
        }
    } catch (err) {
        console.error("Loi Login:", err);
        res.status(500).json({ success: false, message: "Lỗi Server!" });
    }
});

// API CHATBOT 
app.post('/ask', async (req, res) => {
    const { question } = req.body;
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.setHeader('Transfer-Encoding', 'chunked');

    try {
        const aiResponse = await axios({
            method: 'post',
            url: 'http://localhost:8081/ask', 
            data: { question: question },
            responseType: 'stream'
        });

        aiResponse.data.on('data', (chunk) => res.write(chunk));
        aiResponse.data.on('end', () => res.end());
        aiResponse.data.on('error', () => res.end());
    } catch (error) {
        res.write("Lỗi: Không thể kết nối với AI Service.");
        res.end();
    }
});

// --- 5. CHẠY SERVER ---
app.listen(PORT, () => {
    console.log(`Backend đang chạy tại: http://localhost:${PORT}`);
    console.log(`Camera URL hiện tại: ${CAMERA_URL}`);
});