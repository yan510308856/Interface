"""Lazy imports keep smoke checks independent of CUDA / model installation."""
import time
import json
from pathlib import Path


def inspect_local_model(name):
    """Cheap HF directory checks; no torch import, weight loading, or network."""
    root = Path(name).expanduser().resolve()
    config = json.loads((root / "config.json").read_text())
    if not (root / "tokenizer_config.json").is_file() or not (root / "tokenizer.json").is_file():
        raise ValueError("Missing tokenizer_config.json or tokenizer.json")
    index = root / "model.safetensors.index.json"
    names = set(json.loads(index.read_text())["weight_map"].values()) if index.exists() else {"model.safetensors"}
    if not names or any(Path(n).name != n for n in names):
        raise ValueError("Invalid safetensors shard names")
    missing = [n for n in sorted(names) if not (root / n).is_file() or (root / n).stat().st_size == 0]
    if missing:
        raise ValueError("Missing/empty shards (or broken cache symlinks): " + ", ".join(missing))
    return dict(path=str(root), model_type=config.get("model_type"),
                architectures=config.get("architectures"), stored_dtype=config.get("torch_dtype", config.get("dtype")),
                shards=len(names), weight_bytes=sum((root / n).stat().st_size for n in names),
                config=config)


class HFModel:
    def __init__(self, name, revision=None, quantization="none", context_limit=16384):
        import torch
        import transformers
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        if not torch.cuda.is_available():
            raise RuntimeError("Real runs require a CUDA GPU. Use smoke for CPU-only checks.")
        self.torch = torch
        self.context_limit = context_limit
        local = Path(name).expanduser().is_dir()
        source = inspect_local_model(name) if local else None
        if source:
            name = source["path"]
            # Conservative lower-bound check, not a guarantee that remaining KV cache fits.
            free, _ = torch.cuda.mem_get_info()
            if quantization == "none" and source["weight_bytes"] > free * 0.9:
                raise RuntimeError("Local weights exceed available GPU memory. Use --quantization 4bit or a larger GPU.")
        elif name.startswith(("/", "./", "../", "~")):
            raise FileNotFoundError(f"Local model folder not found: {name}")
        options = dict(revision=None if local else revision, local_files_only=local, trust_remote_code=False)
        self.tokenizer = AutoTokenizer.from_pretrained(name, **options)
        quant = None
        if quantization == "4bit":
            quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                      bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
        self.model = AutoModelForCausalLM.from_pretrained(
            name, torch_dtype=torch.bfloat16, device_map={"": 0},
            quantization_config=quant, use_safetensors=True, **options)
        self.model.eval()
        self.metadata = dict(model=name, revision=getattr(self.model.config, "_commit_hash", None),
                             torch=torch.__version__, transformers=transformers.__version__,
                             gpu=torch.cuda.get_device_name(0), quantization=quantization,
                             context_limit=context_limit, local_source=source)
        if quantization == "4bit":
            import bitsandbytes
            self.metadata["bitsandbytes"] = bitsandbytes.__version__
        print(f"Loaded {name}; quantization={quantization}; context={context_limit}", flush=True)

    def count(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def generate(self, messages, *, guard=False, seed=0, max_tokens=2048, deadline=None):
        torch = self.torch
        text = self.tokenizer.apply_chat_template(messages, tokenize=False,
                     add_generation_prompt=True, enable_thinking=False)
        inputs = self.tokenizer(text, return_tensors="pt").to("cuda:0")
        n = inputs.input_ids.shape[1]
        if n + max_tokens > self.context_limit:
            raise RuntimeError("context_overflow")
        if deadline is not None and time.monotonic() >= deadline:
            raise TimeoutError("episode_timeout")
        torch.manual_seed(seed)
        torch.cuda.synchronize()
        start = time.monotonic()
        options = dict(max_new_tokens=max_tokens, do_sample=not guard,
                       pad_token_id=self.tokenizer.eos_token_id)
        if not guard:
            options.update(temperature=0.7, top_p=0.8, top_k=20)
        if deadline is not None:
            options["max_time"] = max(0.01, deadline - start)
        with torch.inference_mode():
            output = self.model.generate(**inputs, **options)
        torch.cuda.synchronize()
        tokens = output[0, n:]
        return dict(text=self.tokenizer.decode(tokens, skip_special_tokens=True),
                    input_tokens=n, output_tokens=len(tokens), seconds=time.monotonic()-start)
