const express = require('express');
const cors = require('cors');
const axios = require('axios'); // Thư viện để gọi API
const app = express();

app.use(cors());
app.use(express.json());

app.post('/ask', async (req, res) => {
    const { question } = req.body;

    // Thiết lập Header để chuẩn bị Stream về cho React
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');

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

    } catch (error) {
        res.write("Lỗi: Không thể kết nối với AI Service.");
        res.end();
    }
});

app.listen(5000, () => console.log('Node.js Backend chạy tại cổng 5000'));