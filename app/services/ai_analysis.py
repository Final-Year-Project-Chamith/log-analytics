MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
MAX_ATTEMPTS = 2
MIN_LOG_LENGTH = 10  
def generate_ai_analysis(logs_text: str, generator) -> str:
    """Generate analysis using AI with strict validation"""
    if not generator or len(logs_text) < MIN_LOG_LENGTH:
        return None
    
    prompt = f"""<|system|>
Generate a Docker log analysis report with exactly these sections:

1. Status Summary: [concise overview]
2. Critical Issues: [bullet points]
3. Resource Trends: [CPU/Memory patterns]
4. Recommended Actions: [specific steps]

Rules:
- Use only information from these logs:
{logs_text}
- Never mention commands or tools
- Be technical and concise</s>
<|user|>
Analyze these logs:</s>
<|assistant|>
"""
    
    for _ in range(MAX_ATTEMPTS):
        print("attempt", MAX_ATTEMPTS)
        try:
            result = generator(
                prompt,
                max_new_tokens=350,
                temperature=0.2,
                top_p=0.9,
                do_sample=False,
                repetition_penalty=1.3
            )[0]['generated_text']
            
            report = result.split("<|assistant|>")[-1].strip()
            if all(
                section in report 
                for section in [
                    "1. Status Summary:", 
                    "2. Critical Issues:", 
                    "3. Resource Trends:", 
                    "4. Recommended Actions:"
                ]
            ):
                return report
        except Exception:
            continue
    
    return None