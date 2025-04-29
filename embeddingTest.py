from langchain_huggingface import HuggingFaceEmbeddings
import torch

# Check PyTorch version and CUDA availability
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")

# Set the device to CPU since we are not using CUDA
device = "cpu"

model_name = "Alibaba-NLP/gte-Qwen2-1.5B-instruct"
# Model kwargs adjusted for CPU (no CUDA)
model_kwargs = {'device': device, 'trust_remote_code': True}
encode_kwargs = {'normalize_embeddings': False}

# Create the HuggingFaceEmbeddings object with the specified device (CPU)
hf = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)

# Perform an embedding query and print the result
result = hf.embed_query("What is 9+10")
print(len(result))
