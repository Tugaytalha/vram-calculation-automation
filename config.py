"""
Configuration for VRAM Calculator Automation
"""

# Model configurations
# Format: (display_name, site_model_name, quantization)
MODELS = [
    ("qwen3:32b-q8_0", "Qwen3-32B", "Q8"),
    ("Gemma-3-27B-IT (FP16)", "Gemma 3 27B", "FP16"),
    ("Think2SQL-14B (FP16)", "Qwen2.5-14B", "FP16"),  # Using Qwen2.5-14B as proxy
    ("Qwen3-30B-A3B (Q8)", "Qwen3-30B-A3B", "Q8"),
]

# Batch sizes to test
BATCH_SIZES = [1, 4, 8]

# Context lengths (in tokens)
CONTEXT_LENGTHS = [
    (2048, "2K"),
    (4096, "4K"),
    (8192, "8K"),
    (16384, "16K"),
    (32768, "32K"),
]

# Concurrent users
CONCURRENT_USERS = [1, 4, 8, 16, 64]

# KV Cache should always be FP16/BF16
KV_CACHE_QUANTIZATION = "FP16 / BF16 (Default)"

# Site URL
VRAM_CALCULATOR_URL = "https://apxml.com/tools/vram-calculator"

# Delay between operations (in seconds)
OPERATION_DELAY = 0.5
PAGE_LOAD_DELAY = 3
RESULT_UPDATE_DELAY = 1.5
