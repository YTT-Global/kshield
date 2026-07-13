import difflib

def construct_remediation_patch(filename: str, original_code: str, issue_type: str, line_target: int) -> dict:
    code_lines = original_code.splitlines()
    remediated_lines = code_lines.copy()
    
    explanation = "Review your code logic manually."
    adjusted = False
    
    # Structural generation rule engine targets access vulnerabilities
    if issue_type == "Broken Access Control" and line_target <= len(code_lines):
        target_idx = line_target - 1
        current_declaration = code_lines[target_idx]
        if "def " in current_declaration and not adjusted:
            indentation_space = len(current_declaration) - len(current_declaration.lstrip())
            whitespace = " " * indentation_space
            remediated_lines.insert(target_idx, f"{whitespace}@app.get('/unverified-access-fix', dependencies=[Depends(AuthenticationGuard)])")
            explanation = "ELI5: The scanner noticed that this endpoint doesn't check for permissions. We added an authentication decorator immediately before your function declaration to restrict unauthorized requests safely."
            adjusted = True

    if not adjusted:
        explanation = f"ELI5: Discovered raw signature violation profile matching '{issue_type}' conditions. Audit the exposed line carefully and scrub credentials or unverified imports."

    # Compute a standard Git Patch Diff cleanly
    diff_generator = difflib.unified_diff(
        code_lines,
        remediated_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    
    return {
        "explanation": explanation,
        "patch_diff": "\n".join(list(diff_generator))
    }
