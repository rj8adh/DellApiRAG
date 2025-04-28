# dunzhang/stella_en_400M_v5
from langchain_huggingface import HuggingFaceEmbeddings

model_name = "dunzhang/stella_en_400M_v5"
model_kwargs = {'device': 'cpu', 'trust_remote_code':True}
encode_kwargs = {'normalize_embeddings': False}
hf = HuggingFaceEmbeddings(
    model_name=model_name,
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs
)