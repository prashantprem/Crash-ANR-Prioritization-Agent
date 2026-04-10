import google.generativeai as genai

from .models import Issue


def suggest_fixes(issues: list[Issue], api_key: str) -> list[Issue]:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    for issue in issues:
        prompt = (
            "This Android app crashed with the following stack trace:\n\n"
            f"{issue.stack_trace}\n\n"
            "In 2-3 sentences, suggest the most likely cause and fix."
        )
        try:
            response = model.generate_content(prompt)
            issue.fix_suggestion = response.text.strip()
        except Exception as e:
            print(f"[fix_suggester] Error for issue {issue.id}: {type(e).__name__}: {e}")
            issue.fix_suggestion = "Unable to generate suggestion."

    return issues
