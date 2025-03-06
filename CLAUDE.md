# Commands
- Build/Run: `make serve` (docker-compose up -d --build)
- Test: `make test` (docker compose run --rm backend pytest)
- Test single file: `docker compose run --rm backend pytest path/to/test.py::TestClass::test_method -v`
- Shell: `make shell` (Django shell_plus with IPython)
- Stripe sync: `make stripe-sync`
- Frontend: `npm run build`, `npm start`, `npm run watch`

# Code Style
## Python
- Line length: 120
- Formatting: black
- Imports: isort (Django profile, combine_as_imports, trailing_comma)
- Linting: ruff
- Django templates: djlint (profile=django)
- Error handling: Proper exception catching and logging

## Frontend
- StimulusJS: Use controllers for all interactive elements
- TailwindCSS: Use for styling (with @tailwindcss/forms, @tailwindcss/typography)
- JavaScript: @babel/eslint-parser, eslint:recommended, required semicolons
- SCSS: stylelint-config-standard-scss

## Naming & Structure
- Follow Django conventions for models, views
- Use type hints in Python
- Follow existing pattern in codebase for component structure
- Document complex functions and classes
