from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen2.5-1.5B-Instruct"
save_path = "./models" # Đường dẫn bạn muốn lưu

# Tải và lưu về máy
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

tokenizer.save_pretrained(save_path)
model.save_pretrained(save_path)

print(f"Đã lưu model vào: {save_path}")