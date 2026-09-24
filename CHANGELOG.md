# Changelog

All notable changes to RoleVerse are documented in this file.

## [Unreleased]

### Added

- Initial product plan and delivery milestones.
- Versioned FastAPI health endpoint.
- Static client shell with chat, discovery, marketplace, and favorites views.
- English and Persian language switching with RTL and LTR layout support.
- Light and dark theme switching with local preference persistence.
- Responsive conversation workspace with character selection and a local preview response.
- Semantic design-system reference for the project.
- Development dependency manifest and API smoke tests.
- Development version marker and documented branch integration workflow.

### Changed

- Replaced the placeholder getting-started section with local development instructions.

### Known limitations

- Authentication is a visual development shell; real OTP persistence is not implemented yet.
- Client conversations use deterministic preview data and are not persisted server-side.
- OpenAI-compatible provider integration is not implemented yet.
- The admin panel and marketplace publishing workflow are not implemented yet.
