# WhatsApp Companion Data Analyzer

[![WhatsApp CLI MacOS](https://github.com/mmahmad/whatsapp-cli-macos/actions/workflows/python-app.yml/badge.svg)](https://github.com/mmahmad/whatsapp-cli-macos/actions/workflows/python-app.yml)

A powerful command-line tool for searching and browsing your local WhatsApp message history on macOS with fuzzy matching, interactive navigation, and conversation viewing.

## Features

- 🔍 **Fuzzy Search**: Find messages even with typos or partial matches
- 💬 **Chat Viewing**: Browse entire conversations chronologically with natural messaging app flow
- 🎯 **Contact Search**: Search within specific contacts or across all conversations
- 📄 **Smart Pagination**: Navigate through results with caching for consistency
- ⚡ **Interactive Mode**: Seamless GUI-like navigation within the CLI
- 🔒 **Privacy First**: All processing happens locally, no data ever leaves your machine
- 📊 **Performance Optimized**: Handles large datasets (100k+ messages) efficiently
- 🎨 **Rich Display**: Clear formatting with emojis and visual separators

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Make executable
chmod +x whatsapp_search.py

# Search all messages
python3 whatsapp_search.py --query "pizza"

# View conversation with a contact
python3 whatsapp_search.py "John Doe"

# Search within specific contact
python3 whatsapp_search.py "Mom" --query "appointment"

# Get database statistics
python3 whatsapp_search.py --stats
```

## Installation

### Prerequisites

- macOS 10.14+ with WhatsApp Desktop installed and synced
- Python 3.6+
- WhatsApp Desktop must have synced your message history

### Setup

1. **Clone or download** this repository
2. **Install Python dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```
3. **Make the script executable:**
   ```bash
   chmod +x whatsapp_search.py
   ```
4. **Verify installation:**
   ```bash
   python3 whatsapp_search.py --stats
   ```

## Basic Usage

### Global Search
```bash
# Search across all conversations
python3 whatsapp_search.py --query "meeting"

# Search with custom threshold and sorting
python3 whatsapp_search.py --query "project" --threshold 80 --sort time
```

### Chat Viewing
```bash
# Browse conversation with a contact (interactive)
python3 whatsapp_search.py "Alice"

# Non-interactive with specific page
python3 whatsapp_search.py "Bob" --page 2 --no-interactive
```

### Contact-Specific Search
```bash
# Search within specific contact's messages
python3 whatsapp_search.py "John" --query "deadline"
```

## Interactive Mode (Default)

The tool uses interactive mode by default for the best user experience:

```
Options: n) Next page | p) Previous page | g) Go to page | l) Change limit | q) Quit
```

- **n/p**: Navigate between pages instantly
- **g**: Jump to any specific page
- **l**: Change results per page (1-100)
- **t/r**: Switch between time/relevance sorting (search mode)
- **c**: Clear cache and refresh (search mode)
- **q**: Quit

No need to re-run commands - all navigation happens within the same session!

## How It Works

The tool automatically discovers and reads from WhatsApp's local SQLite databases stored in your macOS Group Containers:
- `~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite`
- `~/Library/Group Containers/group.net.whatsapp.WhatsApp.private/ChatStorage.sqlite`
- `~/Library/Group Containers/group.net.whatsapp.family/ChatStorage.sqlite`

It uses advanced fuzzy matching with multiple strategies to find messages even with typos, while optimizing performance through database-level filtering and intelligent caching.

## Privacy & Security

- ✅ **100% Local**: All processing happens on your machine
- ✅ **Read-Only**: Never modifies your WhatsApp data
- ✅ **No Network**: Zero data transmission to external servers
- ✅ **Safe Access**: Uses SQLite read-only mode with proper connection handling

## Documentation

- **[Usage Guide](USAGE_GUIDE.md)** - Comprehensive usage examples and command reference
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions
- **[Development Guide](DEVELOPMENT.md)** - Contributing and development setup
- **[Product Requirements](PRD.md)** - Detailed product specification
- **[Engineering Documentation](ENGINEERING_DOC.md)** - Technical architecture and implementation
- **[Backlog](BACKLOG.md)** - Future improvements and enhancement tracking

## Requirements

- **macOS**: 10.14+ with WhatsApp Desktop installed
- **Python**: 3.6+ with sqlite3 module
- **Dependencies**: `fuzzywuzzy`, `python-Levenshtein` (see requirements.txt)
- **WhatsApp**: Desktop app must be installed and message history synced

## Performance

- **Search Speed**: <2 seconds for 50,000+ messages
- **Memory Usage**: ~200-400MB for large datasets
- **Dataset Support**: Tested with 100,000+ messages
- **Caching**: Smart result caching for instant page navigation

## Command Reference

```bash
python3 whatsapp_search.py [CONTACT] [OPTIONS]

Positional Arguments:
  CONTACT               Contact name to view conversation with

Options:
  -q, --query TEXT      Search for specific messages
  -l, --limit INT       Results per page (default: 20)
  -t, --threshold INT   Fuzzy match threshold 0-100 (default: 60)
  -p, --page INT        Page number (default: 1)
  -s, --sort CHOICE     Sort by 'relevance' or 'time' (default: relevance)
  --no-interactive      Disable interactive mode
  --stats               Show database statistics
  -h, --help           Show help message
```

## Development

```bash
# Run tests
python3 -m pytest test_whatsapp_search.py -v

# Run tests directly
python3 test_whatsapp_search.py
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development setup, testing, and contribution guidelines.

## Troubleshooting

**Common Issues:**
- **"No WhatsApp database found"**: Ensure WhatsApp Desktop is installed and has synced messages
- **No search results**: Try lowering the threshold (`--threshold 50`) or using different terms
- **Contact not found**: Try partial names or phone numbers

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions to common problems.

## License

This project is provided as-is for educational and personal use. Ensure compliance with WhatsApp's Terms of Service when using this tool.

## Contributing

Contributions are welcome! Please see [DEVELOPMENT.md](DEVELOPMENT.md) for development setup and contribution guidelines.

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Acknowledgments

- Built with [fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy) for fuzzy string matching
- Uses [python-Levenshtein](https://github.com/ztane/python-Levenshtein) for performance optimization
- Tested with [pytest](https://pytest.org/) framework