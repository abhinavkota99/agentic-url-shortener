# Security and Governance

- Accept only absolute HTTP/HTTPS destination URLs.
- Do not fetch destination URLs from the server. If link preview is added, implement SSRF protections, DNS/IP validation and egress controls.
- Use parameterized JPA access.
- Keep secrets outside source control.
- Run code-generation and test tools in isolated containers with command allowlists, timeouts, CPU/memory limits and restricted network access.
- Require human approval for protected-branch changes, production configuration and deployment.
- Approval is bound to an artifact version; any changed artifact requires a new approval.
- Redact secrets and personal data from prompts, logs and audit records.
- Define analytics retention and privacy controls before production.
- Add authentication and role-based authorization to workflow APIs before external exposure.
