# BLK PHX LABS — Compliance Check Command
# Usage in Claude Code: /compliance-check

Scan all content files and code for FTC/FDA compliance violations.

Check for:
1. Disease treatment claims ("treats", "cures", "prevents", "heals")
2. Absolute efficacy claims ("will improve", "guaranteed to", "proven to")  
3. Missing FDA disclaimer on product-related content
4. Health claims without "may support" or mechanism-only language
5. Any language implying medical advice

Approved language patterns:
- "studied for", "research suggests", "mechanism involves"
- "may support", "formulated to", "designed for"
- Always followed by: FDA disclaimer

Flag any violations with file path + line number.
Report clean if no violations found.
