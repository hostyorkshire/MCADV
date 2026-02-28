# Contributing to MCADV

Thank you for your interest in contributing to MCADV! This document provides guidelines for contributing to the project.

## 🎯 Ways to Contribute

- **Report bugs** - Found an issue? Let us know!
- **Suggest features** - Have ideas for improvements?
- **Submit pull requests** - Code contributions welcome!
- **Improve documentation** - Help make the docs better
- **Share your setup** - Document your deployment experience

## 🐛 Reporting Bugs

Before creating a bug report, please:
1. Check the [existing issues](https://github.com/hostyorkshire/MCADV/issues) to avoid duplicates
2. Review the [troubleshooting guides](guides/)
3. Gather relevant information (logs, hardware specs, configuration)

**When reporting a bug, include:**
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Your hardware setup (Pi model, radio, etc.)
- Software versions (Python, Ollama, MCADV commit)
- Relevant log snippets from `logs/`
- MeshCore radio configuration

## 💡 Suggesting Features

Feature requests are welcome! Please:
- Check if the feature already exists or is planned
- Clearly describe the feature and its use case
- Explain how it benefits the project
- Consider implementation complexity

## 🔧 Development Setup

### 1. Fork and Clone
```bash
git clone https://github.com/YOUR_USERNAME/MCADV.git
cd MCADV
```

### 2. Set Up Environment
```bash
# Create virtual environment
./setup_venv.sh

# Activate it
source venv/bin/activate
```

### 3. Install Development Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Tests
```bash
# Run all tests
./run_all_tests.sh

# Or use the interactive menu
./run_tests_menu.sh
```

## 📝 Code Standards

### Python Style
- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and concise

### Linting
We use `flake8` and `pylint`:
```bash
# Check your code
flake8 .
pylint *.py
```

Configuration files:
- `.flake8` - Flake8 settings
- `.pylintrc` - Pylint settings

### Testing
- Write tests for new features
- Ensure existing tests pass
- Add integration tests for major features
- Test on actual hardware when possible

## 🚀 Pull Request Process

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Your Changes
- Write clear, concise commit messages
- Keep commits focused and atomic
- Reference issues in commits (e.g., "Fixes #123")

### 3. Test Thoroughly
```bash
# Run all tests
./run_all_tests.sh

# Test on hardware if possible
./run_adventure_bot.sh --help
```

### 4. Update Documentation
- Update README.md if needed
- Add/update guides in `guides/` directory
- Update CHANGELOG.md (see versioning section)
- Add docstrings to new code

### 5. Submit Pull Request
- Push your branch to your fork
- Open a PR against `main` branch
- Fill out the PR template completely
- Link related issues
- Request review

### PR Review Checklist
- [ ] Code follows project style guidelines
- [ ] Tests pass (GitHub Actions)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts
- [ ] Commits are clean and descriptive

## 📚 Documentation Guidelines

### Markdown Files
- Use clear, descriptive headings
- Include code examples with syntax highlighting
- Add emojis for visual hierarchy (sparingly)
- Test all commands and code snippets

### Guides
New guides should:
- Go in the `guides/` directory
- Follow the existing format
- Be listed in `guides/README.md`
- Include a "Recommended for" section

### Code Comments
- Explain *why*, not *what*
- Document complex algorithms
- Note hardware-specific considerations
- Include units for timing/performance values

## 🏷️ Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Updating CHANGELOG.md
Add your changes under `[Unreleased]` section:
```markdown
## [Unreleased]

### Added
- New feature description

### Changed
- Modified behavior description

### Fixed
- Bug fix description
```

## 🔒 Security

**Do not** open public issues for security vulnerabilities. Instead:
- Review SECURITY.md
- Contact maintainers privately
- Follow responsible disclosure practices

## 📜 License

By contributing, you agree that your contributions will be licensed under the GNU General Public License v3.0 (GPL-3.0), the same license as the project.

## 💬 Questions?

- Open a [discussion](https://github.com/hostyorkshire/MCADV/issues)
- Review existing [issues and PRs](https://github.com/hostyorkshire/MCADV/pulls)
- Check the [documentation](guides/)

## 🙏 Recognition

Contributors will be:
- Credited in release notes
- Listed in project acknowledgments
- Part of the MCADV community!

Thank you for contributing to MCADV! 🎉