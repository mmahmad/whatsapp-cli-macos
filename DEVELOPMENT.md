# Development Guide
## WhatsApp Companion Data Analyzer

### Development Setup

#### Prerequisites
- macOS 10.14+ with WhatsApp Desktop installed
- Python 3.6+
- Git

#### Getting Started
```bash
# Clone the repository
git clone <repository-url>
cd whatsapp-companion-data-analyzer

# Install dependencies
pip3 install -r requirements.txt

# Make script executable
chmod +x whatsapp_search.py

# Verify installation
python3 whatsapp_search.py --stats
```

### Running Tests

The project includes comprehensive unit tests to ensure functionality and prevent regressions:

```bash
# Run tests with pytest (recommended)
python3 -m pytest test_whatsapp_search.py -v

# Run tests directly
python3 test_whatsapp_search.py

# Run with coverage (if coverage.py installed)
python3 -m pytest test_whatsapp_search.py --cov=whatsapp_search --cov-report=html
```

### Test Coverage

The test suite includes **63 comprehensive tests** covering:
- ✅ **Fuzzy matching behavior** (exact matches vs false positives, typo tolerance)
- ✅ **Message filtering** (short message handling, length checks)
- ✅ **Sender information** (individual vs group message senders, contact resolution)
- ✅ **Contact search** (search within specific contacts, browsing)
- ✅ **Database statistics** (message counts and chat info)
- ✅ **Contact name resolution** (JID to contact name mapping, fallbacks)
- ✅ **Error handling** (empty queries, no matches, invalid contacts)
- ✅ **Pagination functionality** (page navigation, invalid pages, metadata)
- ✅ **Sorting systems** (relevance vs time sorting, tiebreakers)
- ✅ **Combined features** (pagination + sorting, consistency checks)
- ✅ **Performance handling** (large result sets, efficient pagination)
- ✅ **Scoring system** (exact vs fuzzy match scores)
- ✅ **Page caching** (cache consistency, invalidation, key generation)
- ✅ **Performance optimizations** (database filtering, contact pre-loading, typo patterns)
- ✅ **Search efficiency** (empty query handling, exact match optimization, progress indicators)
- ✅ **Database-level filtering** (length constraints, candidate reduction, parameter isolation)
- ✅ **Chat viewing functionality** (pagination, fuzzy matching, message format, edge cases)
- ✅ **Database path discovery** (dynamic path generation, cross-platform safety, error handling)

### Code Structure

```
whatsapp-companion-data-analyzer/
├── whatsapp_search.py           # Main application
├── test_whatsapp_search.py      # Test suite
├── requirements.txt             # Dependencies
├── README.md                    # Project overview
├── PRD.md                      # Product requirements
├── ENGINEERING_DOC.md          # Technical documentation
├── USAGE_GUIDE.md              # Detailed usage instructions
├── TROUBLESHOOTING.md          # Common issues and solutions
├── DEVELOPMENT.md              # This file
└── VISUALIZATION_COMPARISON.md  # UI improvement comparison
```

### Adding New Features

When adding new features:

1. **Write tests first** (Test-Driven Development)
   ```python
   def test_new_feature(self):
       # Test the new functionality
       result = self.searcher.new_method(test_input)
       self.assertEqual(expected_output, result)
   ```

2. **Run existing tests** to ensure no regressions:
   ```bash
   python3 -m pytest test_whatsapp_search.py -v
   ```

3. **Implement the feature** in `whatsapp_search.py`

4. **Update tests** if you change existing behavior

5. **All tests must pass** before committing changes

### Code Style Guidelines

#### Python Code Standards
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings for all public methods
- Keep functions focused and single-purpose
- Use type hints where appropriate

#### Database Interactions
- Always use parameterized queries to prevent SQL injection
- Use read-only database connections (`mode=ro`)
- Handle database connection errors gracefully
- Close connections properly using context managers

#### Error Handling
- Provide clear, actionable error messages
- Handle edge cases gracefully
- Use appropriate exception types
- Log progress for long-running operations

### Performance Considerations

#### Optimization Principles
1. **Database-first filtering**: Reduce data at SQL level before Python processing
2. **Caching strategy**: Cache expensive operations (contact names, search results)
3. **Early termination**: Stop processing when sufficient results found
4. **Memory management**: Use generators and iterators for large datasets
5. **Progress feedback**: Keep users informed during long operations

#### Performance Testing
```python
# Example performance test
def test_large_dataset_performance(self):
    import time
    start_time = time.time()
    
    result = self.searcher.search_messages("test", limit=50)
    
    execution_time = time.time() - start_time
    self.assertLess(execution_time, 5.0)  # Should complete in under 5 seconds
```

### Architecture Patterns

#### WhatsAppSearcher Class Design
- **Single Responsibility**: Each method handles one specific search operation
- **Dependency Injection**: Database path can be overridden for testing
- **Caching Layer**: Results cached by search parameters for consistency
- **Error Boundaries**: Each public method handles its own error cases

#### Interactive Mode Pattern
```python
def interactive_mode_handler():
    """Template for interactive mode functions"""
    while True:
        # 1. Display current state
        display_current_results()
        
        # 2. Show available options
        show_navigation_options()
        
        # 3. Get user input
        try:
            choice = get_user_input()
        except (KeyboardInterrupt, EOFError):
            break
            
        # 4. Process choice and update state
        process_user_choice(choice)
        
        # 5. Handle errors gracefully
        handle_invalid_input()
```

### Testing Strategy

#### Unit Test Structure
```python
class TestFeatureName(unittest.TestCase):
    def setUp(self):
        """Create test database with realistic data"""
        self._create_test_database()
        
    def tearDown(self):
        """Clean up test resources"""
        os.unlink(self.test_db_path)
        
    def test_specific_functionality(self):
        """Test one specific aspect of the feature"""
        # Arrange
        test_input = "test query"
        expected_result = {"results": [], "total_matches": 0}
        
        # Act
        actual_result = self.searcher.method_under_test(test_input)
        
        # Assert
        self.assertEqual(expected_result, actual_result)
```

#### Mock Strategy
- **Database mocking**: Use temporary SQLite databases with test data
- **Path mocking**: Override database path discovery for testing
- **Minimal mocking**: Prefer real database interactions over extensive mocking

### Debugging

#### Built-in Debug Features
- Progress indicators during long operations
- Cache status messages
- Contact matching transparency
- Database statistics command

#### Adding Debug Output
```python
# Add debug prints (remove before committing)
print(f"🔍 Processing {len(candidates)} candidates...")
print(f"📊 Match score: {score}% for query: '{query}'")
print(f"💾 Cache key: {cache_key}")
```

#### Debugging Interactive Mode
```python
# Add debug logging for interactive mode issues
try:
    choice = input("\nChoose an option: ").strip().lower()
    print(f"DEBUG: User chose '{choice}'")  # Debug line
except Exception as e:
    print(f"DEBUG: Input error: {e}")  # Debug line
```

### Database Schema Changes

If WhatsApp updates their database schema:

1. **Test with new WhatsApp version**
2. **Update table/column references** in SQL queries
3. **Add backward compatibility** if possible
4. **Update test database schema** to match
5. **Document breaking changes** in release notes

### Contributing Guidelines

#### Before Submitting Changes
1. Run all tests and ensure they pass
2. Test with realistic WhatsApp databases
3. Verify both interactive and non-interactive modes work
4. Check performance with large datasets
5. Update documentation if needed

#### Code Review Checklist
- [ ] Tests pass
- [ ] No new security vulnerabilities
- [ ] Performance impact considered
- [ ] Error handling implemented
- [ ] Documentation updated
- [ ] Backward compatibility maintained

### Release Process

1. **Update version numbers** (if versioning system added)
2. **Run full test suite**
3. **Test with multiple WhatsApp database versions**
4. **Update documentation**
5. **Create release notes** with new features and breaking changes
6. **Tag release** in version control

### Future Development Considerations

#### Potential Enhancements
- **Export functionality**: CSV, JSON, XML output formats
- **Advanced filtering**: Date ranges, message types, sender filters
- **Configuration system**: User preferences and settings file
- **GUI interface**: Optional graphical interface for non-technical users
- **Cross-platform support**: Windows and Linux compatibility

#### Technical Debt Areas
- **Hard-coded database paths**: Should be configurable
- **Limited error recovery**: Some database errors could be handled better  
- **Memory usage**: Large result sets could use streaming
- **SQL query optimization**: Some queries could be more efficient

### Resources

#### Useful References
- [WhatsApp Database Schema](https://github.com/topics/whatsapp-database) (Community resources)
- [SQLite Documentation](https://sqlite.org/docs.html)
- [Python fuzzywuzzy Library](https://github.com/seatgeek/fuzzywuzzy)
- [macOS Group Containers](https://developer.apple.com/documentation/bundleresources/entitlements/com_apple_security_application-groups)

#### Development Tools
- **DB Browser for SQLite**: Explore WhatsApp database structure
- **pytest**: Advanced testing features and plugins
- **coverage.py**: Code coverage analysis
- **black**: Python code formatting
- **pylint**: Code quality analysis