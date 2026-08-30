# ${{ values.name }}

${{ values.description }}

- Run: `pip install -e ".[dev]" && uvicorn ${{ values.pkg }}.app:app --reload`
- Test: `pytest`
- Docs: `docs/` (Diataxis), rendered by the portal's TechDocs
- Lives at: https://${{ values.name }}.mumchimp.com (behind the estate login)
