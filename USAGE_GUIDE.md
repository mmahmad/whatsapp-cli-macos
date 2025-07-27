# Usage Guide
## WhatsApp Companion Data Analyzer

### Command Line Options

- `chat`: Contact name to view conversation with (positional argument)
- `-q, --query`: Search for specific messages (global search if no chat specified)
- `-l, --limit`: Maximum number of results per page (default: 20)
- `-t, --threshold`: Fuzzy match threshold 0-100 (default: 60)
- `-c, --contact`: Alternative way to specify contact (instead of positional argument)  
- `-p, --page`: Page number for paginated results (default: 1)
- `-s, --sort`: Sort by 'relevance' or 'time' (default: relevance)
- `--no-interactive`: Disable interactive mode (use traditional pagination)
- `--stats`: Show database statistics

### Basic Usage Examples

#### Global Message Search
```bash
# Search for messages containing "pizza" (global search)
python3 whatsapp_search.py --query "pizza"

# Search with custom limit and threshold
python3 whatsapp_search.py --query "pizza" --limit 10 --threshold 70

# Paginated search - view more results
python3 whatsapp_search.py --query "pizza" --page 2

# Sort by time instead of relevance
python3 whatsapp_search.py --query "pizza" --sort time

# Traditional non-interactive mode (if needed)
python3 whatsapp_search.py --query "pizza" --no-interactive
```

#### View Entire Conversations
```bash
# View entire conversation with a contact (interactive mode)
python3 whatsapp_search.py "John"

# View conversation with pagination (non-interactive)
python3 whatsapp_search.py "Mom" --limit 10 --page 2 --no-interactive

# Interactive chat viewing with custom page size
python3 whatsapp_search.py "Alice" --limit 5
```

#### Search Within Specific Contact
```bash
# Search for messages from/to "John" containing "meeting"
python3 whatsapp_search.py "John" --query "meeting"

# Browse messages from "Mom" containing "appointment" with pagination
python3 whatsapp_search.py "Mom" --query "appointment" --limit 10 --page 2

# Interactive contact search with pagination
python3 whatsapp_search.py "John" --query "project"
```

#### Database Statistics
```bash
# Show statistics about your WhatsApp database
python3 whatsapp_search.py --stats
```

### Interactive Mode 🎮 (Default)

The tool uses **interactive mode by default** for the best user experience:

#### Features
```
Options: n) Next page | p) Previous page | t) Sort by time | r) Sort by relevance | g) Go to specific page | l) Change page size | c) Clear cache (force refresh) | q) Quit
```

- **🔄 Seamless Navigation**: Use `n`/`p` for next/previous pages
- **🔀 Dynamic Sorting**: Switch between relevance/time with `t`/`r`
- **🎯 Jump to Page**: Use `g` to go directly to any page
- **📏 Adjust Page Size**: Use `l` to change results per page (1-100)
- **📄 Page Caching**: Visited pages are cached for instant, consistent navigation
- **🗑️ Cache Control**: Use `c` to clear cache and force refresh from database
- **⚡ No Re-running**: All navigation happens within the same session

#### Example Session
```bash
# Start interactive global search (default behavior)
python3 whatsapp_search.py --query "appointment"

# Start interactive chat viewing (default behavior)
python3 whatsapp_search.py "John Doe"

# Navigate with single keystrokes:
# n → next page
# p → previous page  
# t → sort by time (most recent first) [search only]
# r → sort by relevance (best matches first) [search only]
# g → jump to specific page
# l → change page size
# c → clear cache (force refresh) [search only]
# q → quit
```

#### Why Interactive Mode is Default?
- **Better UX**: No need to exit and re-run commands
- **Faster**: Instant navigation between pages and sorting modes
- **Flexible**: Change page size and jump to any page on the fly
- **Intuitive**: Most users prefer GUI-like navigation over command-line parameters

#### When to Use Non-Interactive Mode?
Use `--no-interactive` for:
- **Scripts/Automation**: When programmatically processing results
- **Single Page**: When you only need one specific page
- **Redirecting Output**: When piping results to other commands

### Pagination and Sorting

The search retrieves **all matching messages** from your database and provides pagination:

#### **Pagination**
- **Default**: 20 results per page
- **Navigate**: Use `--page 2`, `--page 3`, etc. to browse
- **Total count**: Shows total matches and page info
- **Hints**: Tool suggests next page commands

#### **Sorting Options**
- **Relevance (default)**: Best matches first, then by time
- **Time**: Most recent messages first, then by relevance

#### **Example Workflow**
```bash
# Initial search - see first 20 best matches (global search)
python3 whatsapp_search.py --query "project"

# Output shows: "Found 347 matching messages, Page 1 of 18"
# Browse more results
python3 whatsapp_search.py --query "project" --page 2

# Or switch to time-based to see recent mentions
python3 whatsapp_search.py --query "project" --sort time
```

### Chat Viewing 💬

The tool supports viewing entire conversations with any contact with natural messaging app flow:

#### **Features**
- **📜 Complete Conversations**: View all messages exchanged with a specific contact
- **🕒 Natural Flow**: Recent conversations first, chronological order within each page (like messaging apps)
- **📄 Full Pagination**: Navigate through long conversations with ease
- **🎯 Fuzzy Contact Matching**: Find contacts even with partial names or typos
- **🎨 Conversation Format**: Clean display optimized for chat viewing
- **⚡ Interactive Navigation**: Seamless browsing with single-key commands

#### **Usage Examples**
```bash
# Interactive chat viewing (default)
python3 whatsapp_search.py "John Doe"

# Non-interactive with pagination
python3 whatsapp_search.py "Mom" --limit 15 --page 2 --no-interactive

# Fuzzy matching works for contact names
python3 whatsapp_search.py "Ali"  # Matches "Alice Smith"
```

#### **Interactive Navigation**
In interactive mode, you can:
- **`n`** - Next page of messages
- **`p`** - Previous page of messages  
- **`g`** - Jump to specific page number
- **`l`** - Change messages per page (1-100)
- **`q`** - Quit chat viewing

#### **Conversation Flow**
- **Page 1**: Shows most recent messages (chronological order within page)
- **Page 2**: Shows older messages (chronological order within page)  
- **Natural Reading**: Read top to bottom within each page, no scrolling up needed
- **Recent First**: Most recent conversations appear on page 1

### Page Caching & Consistency 📄

The search tool caches all results for a search session to ensure:

- **Consistent Navigation**: Going back to a previous page shows identical results as before
- **Performance**: Previously visited pages load instantly from cache
- **Data Integrity**: No risk of getting different results when navigating back and forth
- **Smart Invalidation**: Cache automatically clears when search parameters change (query, threshold, sort)

```bash
# Example: Consistent page navigation (global search)
python3 whatsapp_search.py --query "meeting"
# Page 1: Shows results A, B, C
# Press 'n' → Page 2: Shows results D, E, F  
# Press 'p' → Page 1: Shows identical results A, B, C (from cache)
# Press 'c' → Clears cache, forces fresh database query
```

### Advanced Examples

```bash
# Find messages about "lunch" with high accuracy (global search)
python3 whatsapp_search.py --query "lunch" --threshold 80

# Find recent messages from Mom (view entire conversation)
python3 whatsapp_search.py "Mom" --limit 15

# Search for messages containing "appointment" or similar (global search)
python3 whatsapp_search.py --query "appointmnt" --threshold 50

# Browse through all results with pagination (global search)
python3 whatsapp_search.py --query "meeting" --limit 10 --page 3

# Get most recent messages containing "work" (sorted by time, global search)
python3 whatsapp_search.py --query "work" --sort time --limit 5

# Interactive browsing (default) - best user experience (global search)
python3 whatsapp_search.py --query "meeting"

# Traditional mode for scripts/automation (global search)
python3 whatsapp_search.py --query "meeting" --no-interactive --page 2

# Get database overview
python3 whatsapp_search.py --stats

# View entire conversation with someone
python3 whatsapp_search.py "John Doe"

# Browse conversation pages non-interactively
python3 whatsapp_search.py "Alice" --limit 5 --page 2 --no-interactive

# Search within specific contact's messages
python3 whatsapp_search.py "John" --query "project"
```